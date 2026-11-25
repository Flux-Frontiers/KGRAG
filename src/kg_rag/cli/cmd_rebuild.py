"""
cmd_rebuild.py

kgrag rebuild-indices -- rebuild every registered KG with its own builder.

Walks the registry (or one corpus), runs each KG's own ``build`` command in
the folder that holds its store, and reports each KG as built, failed or
skipped. Use it after an SDK change alters what a store records, such as
kgmodule-utils 0.32.0's source hashes.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.config import read_builder_version
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry

console = Console()

# kind -> (builder CLI, flag that names the build root, or None for a
# positional root). Every builder reads the rest of its inputs (GEDCOM files,
# the diary source, include/exclude lists) from its own store or pyproject.
_BUILDERS: dict[KGKind, tuple[str, str | None]] = {
    KGKind.CODE: ("pycodekg", "--repo"),
    KGKind.DOC: ("dockg", "--repo"),
    KGKind.FILETREE: ("ftreekg", "--repo"),
    KGKind.TYPESCRIPT: ("tscodekg", "--repo"),
    KGKind.SWIFT: ("swiftkg", "--repo"),
    KGKind.MEMORY: ("memorykg", "--repo"),
    KGKind.GENEALOGY: ("genkg", "--repo"),
    KGKind.VAULT: ("vaultkg", "--vault"),
    KGKind.DIARY: ("diarykg", None),
}

# Kinds never rebuilt here, with the reason reported for each.
_SKIP_REASONS: dict[KGKind, str] = {
    KGKind.AGENT: "conversation memory; the store is its own source",
    KGKind.GUTENBERG: "static corpus; rebuild with gutenkg ingest",
    KGKind.IA: "static corpus; rebuild with gutenkg",
    KGKind.CONNECTOME: "needs the Codex data folder; rebuild with connkg build",
}


def build_root(entry: KGEntry) -> Path:
    """Return the folder a KG's builder runs in: the parent of its store folder.

    :param entry: The registry entry.
    :return: ``<root>`` for a store at ``<root>/.<x>kg/graph.sqlite``, else the
        entry's ``repo_path``.
    """
    if entry.sqlite_path is not None:
        return entry.sqlite_path.parent.parent
    return entry.repo_path


def find_builder(name: str, entry: KGEntry) -> str | None:
    """Locate a builder CLI: on PATH first, then in a venv near the KG.

    The venv fallbacks are the entry's recorded venv, then the nearest
    ``.venv`` at or above the build root. A corpus entry such as
    ``genealogy_kg/corpora/entries/<x>`` records a venv inside itself that
    does not exist; its builder is in ``genealogy_kg/.venv``.

    :param name: The CLI name, such as ``pycodekg``.
    :param entry: The registry entry.
    :return: The executable's path, or None when none has it.
    """
    found = shutil.which(name)
    if found:
        return found
    root = build_root(entry)
    for venv in (entry.venv_path, *(d / ".venv" for d in (root, *root.parents))):
        local = venv / "bin" / name
        if local.is_file():
            return str(local)
    return None


def plan(entry: KGEntry) -> tuple[list[str] | None, str]:
    """Return the build command for one KG, or None and the reason it is skipped.

    :param entry: The registry entry.
    :return: ``(argv, "")`` to build, or ``(None, reason)`` to skip.
    """
    if entry.kind in _SKIP_REASONS:
        return None, _SKIP_REASONS[entry.kind]
    if entry.kind not in _BUILDERS:
        return None, f"no builder known for kind {entry.kind.value!r}"
    root = build_root(entry)
    if not root.is_dir():
        return None, f"folder missing: {root}"
    cli_name, root_flag = _BUILDERS[entry.kind]
    exe = find_builder(cli_name, entry)
    if exe is None:
        return None, f"{cli_name} not on PATH or in a .venv at or above {root}"
    root_args = [root_flag, str(root)] if root_flag else [str(root)]
    return [exe, "build", *root_args], ""


def _select(
    reg: KGRegistry,
    corpus: str | None,
    kinds: tuple[str, ...],
    names: tuple[str, ...],
    db: Path | None,
) -> list[KGEntry]:
    """Return the registry entries the options name, in registry order.

    :param reg: The open KG registry.
    :param corpus: Restrict to this corpus's members, or None.
    :param kinds: Restrict to these kinds; empty means every kind.
    :param names: Restrict to these KG names; empty means every name.
    :param db: The registry path, for opening the corpus registry.
    :return: The selected entries.
    :raises click.ClickException: When the corpus does not exist.
    """
    entries = reg.list()
    if corpus:
        with CorpusRegistry(db_path=db) as corp_reg:
            found = corp_reg.get(corpus)
        if found is None:
            raise click.ClickException(f"Corpus not found: {corpus!r}")
        members = set(found.kg_ids)
        entries = [e for e in entries if e.id in members]
    if kinds:
        wanted = {KGKind.from_str(k) for k in kinds}
        entries = [e for e in entries if e.kind in wanted]
    if names:
        entries = [e for e in entries if e.name in set(names)]
    return entries


@cli.command("rebuild-indices")
@click.option("--corpus", default=None, metavar="NAME", help="Rebuild only this corpus's KGs.")
@click.option(
    "--kind",
    "kinds",
    multiple=True,
    type=click.Choice([k.value for k in KGKind], case_sensitive=False),
    help="Rebuild only KGs of this kind (repeatable).",
)
@click.option(
    "--name", "names", multiple=True, metavar="NAME", help="Rebuild only this KG (repeatable)."
)
@click.option("--dry-run", is_flag=True, help="Print each command or skip reason; build nothing.")
@registry_option
def rebuild_indices(corpus, kinds, names, dry_run, registry):
    """Rebuild every registered KG with its own builder.

    Each KG is rebuilt by its kind's CLI (pycodekg, dockg, ftreekg, tscodekg,
    swiftkg, memorykg, genkg, vaultkg, diarykg), found on PATH first and then
    in the nearest .venv at or above the KG, and run in the folder that holds
    its store. Agent,
    Gutenberg, Internet Archive and connectome KGs are skipped. After a build,
    the registry's builder version is re-read from the store.

    Exits 1 when any build fails.

    \b
    Examples:
        kgrag rebuild-indices --dry-run
        kgrag rebuild-indices --kind code --kind doc
        kgrag rebuild-indices --corpus KGRAG_repos
    """
    db = Path(registry).resolve() if registry else None
    rows: list[tuple[str, str, str, str]] = []
    with KGRegistry(db_path=db) as reg:
        entries = _select(reg, corpus, kinds, names, db)
        for entry in entries:
            argv, reason = plan(entry)
            if argv is None:
                rows.append((entry.name, entry.kind.value, "skipped", reason))
                continue
            command = " ".join(argv)
            if dry_run:
                rows.append((entry.name, entry.kind.value, "would build", command))
                continue
            console.rule(f"[bold]{entry.name}[/bold]")
            console.print(f"Running: {command}")
            result = subprocess.run(argv, cwd=build_root(entry), check=False)
            if result.returncode != 0:
                rows.append((entry.name, entry.kind.value, "failed", f"exit {result.returncode}"))
                continue
            version = read_builder_version(entry.sqlite_path)
            if version != "unknown" and version != entry.builder_version:
                reg.update(entry.id, builder_version=version)
            rows.append((entry.name, entry.kind.value, "built", command))

    style = {"built": "green", "would build": "cyan", "failed": "red", "skipped": "yellow"}
    table = Table(title="KG rebuild", box=box.ROUNDED)
    table.add_column("KG", style="bold")
    table.add_column("Kind", style="magenta")
    table.add_column("Status")
    table.add_column("Command or reason", overflow="fold")
    for name, kind, status, detail in rows:
        table.add_row(name, kind, f"[{style[status]}]{status}[/{style[status]}]", detail)
    console.print(table)

    counts = {s: sum(1 for r in rows if r[2] == s) for s in style}
    console.print("  ".join(f"[bold]{s.capitalize()}[/bold] {n}" for s, n in counts.items() if n))
    if counts["failed"]:
        raise SystemExit(1)
