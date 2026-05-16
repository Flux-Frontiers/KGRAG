#!/usr/bin/env python3
"""
build_kg.py — KGRAG Volume Builder

Builds GutenbergKG and/or MetaboKG indices inside a RunPod pod and syncs
them to the Network Volume.

Usage
-----
  # Full build from scratch (first run)
  python build_kg.py

  # Rebuild indices only (repos + venv already present)
  python build_kg.py --rebuild-only

  # One corpus only
  python build_kg.py --metabo-only
  python build_kg.py --gutenberg-only --skip-download

  # Custom destination and genres
  python build_kg.py --dest /data --genres philosophy science
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RED = "\033[31m"


def _c(color: str, text: str) -> str:
    return f"{color}{text}{_RESET}" if sys.stdout.isatty() else text


def info(msg: str) -> None:
    print(_c(_CYAN, f"==> {msg}"), flush=True)


def step(msg: str) -> None:
    print(_c(_GREEN, f"    {msg}"), flush=True)


def warn(msg: str) -> None:
    print(_c(_YELLOW, f"    WARNING: {msg}"), flush=True)


def error(msg: str) -> None:
    print(_c(_RED, f"ERROR: {msg}"), file=sys.stderr, flush=True)


def blank() -> None:
    print(flush=True)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def run(
    cmd: list[str | Path],
    *,
    cwd: Path | None = None,
    env: dict | None = None,
    prefix: str = "    ",
    check: bool = True,
) -> int:
    """Run a command, streaming output line-by-line.

    Iterating proc.stdout in text mode strips \\r automatically, so tqdm /
    rich progress bars never corrupt subsequent log lines.
    """
    proc = subprocess.Popen(
        [str(c) for c in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env or os.environ.copy(),
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip("\r\n")
        if line:
            print(f"{prefix}{line}", flush=True)
    rc = proc.wait()
    if check and rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)
    return rc


def _du(path: Path) -> str:
    try:
        out = subprocess.run(
            ["du", "-sh", str(path)], capture_output=True, text=True, check=False
        ).stdout
        return out.split()[0] if out else "?"
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dest",
        type=Path,
        default=Path(os.environ.get("DEST", "/workspace")),
        help="Network Volume mount path (default: /workspace)",
    )
    p.add_argument(
        "--genres",
        nargs="+",
        default=None,
        metavar="GENRE",
        help=(
            "Gutenberg genres to download/ingest. "
            "In --rebuild-only mode, defaults to all genres present in the corpus dir. "
            "In full mode, defaults to: philosophy english-literature russian-literature"
        ),
    )
    p.add_argument(
        "--metabo-only",
        action="store_true",
        help="Build MetaboKG only; skip GutenbergKG",
    )
    p.add_argument(
        "--gutenberg-only",
        action="store_true",
        help="Build GutenbergKG only; skip MetaboKG",
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip Gutenberg book downloads; ingest from existing corpus",
    )
    p.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Skip system deps, venv creation, and repo cloning; just rebuild indices",
    )
    p.add_argument(
        "--metabo-repo-url",
        default=os.environ.get(
            "METABO_REPO_URL", "https://github.com/Flux-Frontiers/metabo_kg.git"
        ),
        metavar="URL",
        help="MetaboKG git URL",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def setup_env(dest: Path) -> None:
    """Redirect all temp/cache I/O to the volume (root fs is only ~5 GB)."""
    cache_dirs: dict[str, Path] = {
        "TMPDIR": dest / ".tmp",
        "PIP_CACHE_DIR": dest / ".pip_cache",
        "PIP_TMPDIR": dest / ".tmp",
        "PIP_BUILD": dest / ".tmp" / "pip_build",
        "HF_HOME": dest / ".hf_cache",
    }
    for var, path in cache_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[var] = str(path)

    os.environ.update(
        {
            "HF_HUB_OFFLINE": "0",
            "TRANSFORMERS_OFFLINE": "0",
            "HF_DATASETS_OFFLINE": "0",
            "HF_HUB_ENABLE_HF_TRANSFER": "0",  # avoid sporadic transfer failures
        }
    )


# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------

_SYSTEM_PACKAGES = [
    "python3.12",
    "python3.12-venv",
    "python3-pip",
    "git",
    "rsync",
    "libgomp1",
    "libglib2.0-0",
    "curl",
    "tmux",
]


def install_system_deps() -> None:
    info("Installing system dependencies …")
    run(["apt-get", "update", "-qq"])
    run(["apt-get", "install", "-y", "--no-install-recommends", *_SYSTEM_PACKAGES])
    run(["apt-get", "clean"])
    subprocess.run(["rm", "-rf", "/var/lib/apt/lists/"], check=False)
    step("system deps ready")


# ---------------------------------------------------------------------------
# Python venv
# ---------------------------------------------------------------------------


def ensure_venv(work_dir: Path) -> Path:
    venv = work_dir / "venv"
    pip = venv / "bin" / "pip"
    if pip.exists():
        step(f"reusing venv at {venv}")
        return venv
    info(f"Creating venv at {venv} …")
    shutil.rmtree(venv, ignore_errors=True)
    venv.parent.mkdir(parents=True, exist_ok=True)
    run(["python3.12", "-m", "venv", str(venv)])
    run([pip, "install", "--quiet", "--upgrade", "pip"])
    return venv


# ---------------------------------------------------------------------------
# Repo cloning
# ---------------------------------------------------------------------------


def _clone_or_pull(url: str, dest: Path) -> None:
    if (dest / ".git").exists():
        step(f"{dest.name}: pulling latest")
        run(["git", "-C", str(dest), "pull", "--quiet"])
    else:
        step(f"cloning {url}")
        run(["git", "clone", "--quiet", url, str(dest)])


def clone_repos(work_dir: Path, metabo_url: str, gutenberg_only: bool) -> None:
    info("Cloning repos …")
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    subprocess.run(["git", "config", "--global", "credential.helper", ""], check=False)
    _clone_or_pull("https://github.com/Flux-Frontiers/KGRAG.git", work_dir / "kgrag")
    _clone_or_pull("https://github.com/Flux-Frontiers/gutenberg_kg.git", work_dir / "gutenberg_kg")
    if not gutenberg_only:
        _clone_or_pull(metabo_url, work_dir / "Metabo_kg")


def install_packages(venv: Path, work_dir: Path, gutenberg_only: bool) -> None:
    pip = venv / "bin" / "pip"
    info("Installing Python packages …")
    run([pip, "install", "--quiet", "-e", f"{work_dir / 'kgrag'}[kg]"])
    run([pip, "install", "--quiet", "-e", str(work_dir / "gutenberg_kg")])
    metabo_dir = work_dir / "Metabo_kg"
    if not gutenberg_only and metabo_dir.exists():
        run([pip, "install", "--quiet", "-e", str(metabo_dir)])
    step("packages installed")


# ---------------------------------------------------------------------------
# MetaboKG
# ---------------------------------------------------------------------------

_METABO_DATASETS: dict[str, str] = {
    "hsa_pathways": "hsa.sqlite",
    "cge_pathways": "cge.sqlite",
    "icho_model": "icho.sqlite",
}


def build_metabokg(venv: Path, work_dir: Path, dest: Path) -> None:
    info("Building MetaboKG indices …")
    metabokg = venv / "bin" / "metabokg"
    metabo_src = work_dir / "Metabo_kg"

    for dataset, db_name in _METABO_DATASETS.items():
        data_dir = metabo_src / "data" / dataset
        if not data_dir.is_dir():
            warn(f"{data_dir} not found, skipping")
            continue

        step(f"Building {dataset} …")
        index_dir = data_dir / ".metabokg"
        index_dir.mkdir(parents=True, exist_ok=True)

        run(
            [
                metabokg,
                "build",
                "--data",
                str(data_dir),
                "--db",
                str(index_dir / db_name),
                "--lancedb",
                str(index_dir / "lancedb"),
            ]
        )

        dest_dir = dest / "metabo_kg" / "data" / dataset / ".metabokg"
        dest_dir.mkdir(parents=True, exist_ok=True)
        run(["rsync", "-a", f"{index_dir}/", f"{dest_dir}/"])
        step(f"Synced → {dest_dir}  ({_du(dest_dir)})")


# ---------------------------------------------------------------------------
# GutenbergKG
# ---------------------------------------------------------------------------


def build_gutenbergkg(
    venv: Path,
    work_dir: Path,
    dest: Path,
    genres: list[str],
    skip_download: bool,
) -> None:
    info("Building GutenbergKG indices …")
    gutenkg = venv / "bin" / "gutenkg"
    gutenberg_src = work_dir / "gutenberg_kg"

    for genre in genres:
        blank()
        step(f"Genre: {genre}")

        if not skip_download:
            step("Downloading …")
            run(
                [gutenkg, "download", "fetch-genre", genre, "--max-results", "200", "--yes"],
                cwd=gutenberg_src,
            )

        step("Ingesting (building DocKG) …")
        run(
            [gutenkg, "ingest", "--genre", genre, "--force-build"],
            cwd=gutenberg_src,
        )

    blank()
    step("Syncing to volume …")
    gutenberg_dest = dest / "gutenberg_kg"
    gutenberg_dest.mkdir(parents=True, exist_ok=True)
    src_dockg = gutenberg_src / ".dockg"
    dest_dockg = gutenberg_dest / ".dockg"
    dest_dockg.mkdir(parents=True, exist_ok=True)
    run(["rsync", "-a", f"{src_dockg}/", f"{dest_dockg}/"])
    step(f"Done: {_du(dest_dockg)}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(dest: Path) -> None:
    blank()
    print("=" * 60)
    print("  Volume contents:")
    candidates = [
        dest / "gutenberg_kg" / ".dockg",
        *[dest / "metabo_kg" / "data" / ds / ".metabokg" for ds in _METABO_DATASETS],
    ]
    for path in candidates:
        if path.exists():
            print(f"    {_du(path):>6}  {path}")
    blank()
    print("  All done. Terminate this pod — the Network Volume is ready.")
    print(f"  Attach volume to the KGRAG worker with: KG_VOLUME={dest}")
    print("=" * 60)


_DEFAULT_GENRES = ["philosophy", "english-literature", "russian-literature"]


def resolve_genres(args: argparse.Namespace, work_dir: Path) -> list[str]:
    """Return the genre list to process.

    If --genres was given explicitly, use it.  Otherwise:
    - --rebuild-only: auto-detect from the corpus directory on the volume.
    - full mode: fall back to the standard three genres.
    """
    if args.genres is not None:
        return args.genres

    if args.rebuild_only:
        corpus_dir = work_dir / "gutenberg_kg" / "corpus"
        if corpus_dir.is_dir():
            detected = sorted(
                p.name for p in corpus_dir.iterdir() if p.is_dir() and p.name not in ("authors",)
            )
            if detected:
                step(f"Auto-detected {len(detected)} genres from {corpus_dir}")
                return detected
        warn(f"Corpus dir not found at {corpus_dir}; falling back to defaults")

    return _DEFAULT_GENRES


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    dest: Path = args.dest
    work_dir = dest / "kgrag_build"

    setup_env(dest)

    genres = resolve_genres(args, work_dir)

    print("=" * 60)
    print("  KGRAG Volume Builder")
    print(f"  Destination : {dest}")
    if not args.metabo_only:
        print(f"  Genres      : {' '.join(genres)}")
    if args.rebuild_only:
        print("  Mode        : rebuild indices only")
    print("=" * 60)
    blank()

    if not args.rebuild_only:
        install_system_deps()
        venv = ensure_venv(work_dir)
        clone_repos(work_dir, args.metabo_repo_url, args.gutenberg_only)
        install_packages(venv, work_dir, args.gutenberg_only)
    else:
        venv = work_dir / "venv"
        if not (venv / "bin" / "pip").exists():
            error(f"venv not found at {venv} — run without --rebuild-only first.")
            sys.exit(1)
        step(f"using existing venv at {venv}")

    if not args.gutenberg_only:
        build_metabokg(venv, work_dir, dest)

    if not args.metabo_only:
        build_gutenbergkg(venv, work_dir, dest, genres, args.skip_download)

    print_summary(dest)


if __name__ == "__main__":
    main()
