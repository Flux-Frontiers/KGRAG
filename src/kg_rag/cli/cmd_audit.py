"""
cmd_audit.py

LanceDB retirement audit — find every KG still carrying a LanceDB vector
index and report what it takes to move it to sqlite-vec.

The fleet is mid-migration: pycode-kg >=0.20.0 is sqlite-vec only, and
doc-kg >=0.18.1 defaults to sqlite-vec for fresh corpora while still
reading an existing ``lancedb/`` directory.  That means LanceDB residue
survives in three independent places, and a KG can carry any combination
of them:

1. **Registry** — the row still records a ``lancedb_path``.
2. **Disk** — a ``lancedb/`` directory is still present (and still costing
   space) even when nothing reads it any more.
3. **Not yet migrated** -- no *populated* ``vectors.sqlite`` exists, so
   LanceDB is still the live index and must be converted before it can be
   removed.  The file being present is not the test: a failed or interrupted
   migration leaves a zero-table stub, and counting that as migrated would
   turn the remediation into ``rm -rf`` of the only surviving index.

``kgrag audit-lancedb`` reports all three and emits the exact remediation
command per KG.  It never modifies anything.

Usage::

    kgrag audit-lancedb                    # audit the whole registry
    kgrag audit-lancedb --corpus mycorpus  # audit one corpus
    kgrag audit-lancedb my-kg              # audit a single KG
    kgrag audit-lancedb --commands         # print only the fix commands
    kgrag audit-lancedb --json             # machine-readable output
"""

from __future__ import annotations

import contextlib
import json
import shlex
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import KGEntry
from kg_rag.registry import KGRegistry

console = Console()

# Kinds whose index is built by doc-kg, and so can be converted in place by
# ``dockg convert-index`` (reads vectors straight out of LanceDB — no model
# load, no re-embedding).  Every other kind has to be rebuilt to migrate.
_DOCKG_KINDS: frozenset[str] = frozenset({"doc", "gutenberg", "ia"})

# kind → default KG directory name, used to locate an unregistered lancedb/.
_KIND_DB_DIR: dict[str, str] = {
    "code": ".pycodekg",
    "doc": ".dockg",
    "meta": ".metakg",
    "diary": ".diarykg",
    "verse": ".versekg",
    "memory": ".memorykg",
    "disulfide": ".disulfidekg",
    "pdbfile": ".pdbfilekg",
    "legal": ".legalkg",
    "person": ".personkg",
    "gutenberg": ".gutenbergkg",
    "ia": ".iakg",
}

# Audit verdicts, ordered worst-first for display.
_STATUS_ORDER: dict[str, int] = {
    "unmigrated": 0,
    "residue": 1,
    "stale-row": 2,
    "clean": 3,
    "no-index": 4,
}
_STATUS_STYLE: dict[str, str] = {
    "unmigrated": "bold red",
    "residue": "yellow",
    "stale-row": "cyan",
    "clean": "green",
    "no-index": "dim",
}
_STATUS_BLURB: dict[str, str] = {
    "unmigrated": "LanceDB is still the live index — convert it",
    "residue": "migrated, but the LanceDB dir is still on disk",
    "stale-row": "registry references LanceDB that is already gone",
    "clean": "sqlite-vec only",
    "no-index": "no vector index of either kind",
}
# Short verb shown per row; the full command lives behind --commands, which
# keeps the table readable when hundreds of corpora need the same fix.
# "unmigrated" resolves per-kind — only doc-family KGs can convert in place.
_STATUS_ACTION: dict[str, str] = {
    "unmigrated": "convert index",
    "residue": "delete lancedb dir",
    "stale-row": "re-register",
}


@dataclass
class LanceFinding:
    """One KG's LanceDB migration state.

    :param name: Registry name of the KG.
    :param kind: KG kind string (``code``, ``doc``, …).
    :param status: One of ``unmigrated``, ``residue``, ``stale-row``,
        ``clean``, ``no-index``.
    :param registry_reference: True if the registry row records a ``lancedb_path``.
    :param lancedb_dirs: LanceDB directories found on disk.
    :param reclaimable_bytes: Total size of those directories.
    :param has_vectors: True if a *populated* sqlite-vec store exists for
        this KG; a present-but-empty ``vectors.sqlite`` reads as False.
    :param vectors_path: The sqlite-vec store, if one was found.
    :param fix_cmd: Suggested remediation command, or None when nothing to do.
    :param action: Short human-readable verb summarising ``fix_cmd``.
    """

    name: str
    kind: str
    status: str
    registry_reference: bool
    lancedb_dirs: list[str] = field(default_factory=list)
    reclaimable_bytes: int = 0
    has_vectors: bool = False
    vectors_path: str | None = None
    fix_cmd: str | None = None
    action: str = ""


def _dir_size(path: Path) -> int:
    """Return the total size in bytes of every file under *path*.

    :param path: Directory to measure.
    :return: Total bytes, or 0 if the tree is unreadable.
    """
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except OSError:
        return total
    return total


def _kg_dir(entry: KGEntry) -> Path:
    """Return the directory holding this KG's databases.

    Prefers the parent of the recorded SQLite file, falling back to the
    well-known marker directory for the kind.

    :param entry: The registry entry.
    :return: Absolute path to the KG's database directory.
    """
    if entry.sqlite_path:
        return Path(entry.sqlite_path).parent
    return entry.repo_path / _KIND_DB_DIR.get(entry.kind.value, f".{entry.kind.value}kg")


def _find_lancedb_dirs(entry: KGEntry) -> list[Path]:
    """Locate every LanceDB directory belonging to *entry*.

    Checks the recorded ``lancedb_path`` and the default layout, so a
    directory left behind without a registry row is still reported.

    :param entry: The registry entry.
    :return: Deduplicated list of existing LanceDB directories.
    """
    candidates = []
    if entry.lancedb_path:
        candidates.append(Path(entry.lancedb_path))
    candidates.append(_kg_dir(entry) / "lancedb")

    seen: dict[Path, None] = {}
    for c in candidates:
        if c.is_dir():
            seen.setdefault(c.resolve(), None)
    return list(seen)


def _is_populated_vector_store(path: Path) -> bool:
    """Report whether ``path`` is a sqlite-vec store that actually holds vectors.

    Existence is not enough. A ``vectors.sqlite`` can be present and useless:
    an interrupted or failed migration leaves a zero-table file behind, and to
    a check that only calls :meth:`Path.exists` that stub is indistinguishable
    from a finished migration. Treating it as finished is dangerous rather than
    merely wrong -- it downgrades the KG from ``unmigrated`` to ``residue``,
    and ``residue``'s remediation is ``rm -rf`` of the LanceDB directory that
    is, in that state, still the only copy of the index.

    ``vec_meta`` is the plain table :mod:`kg_utils.vector_backend` creates
    alongside the ``vec_nodes`` ``vec0`` virtual table, one row per indexed
    node. It is deliberately the thing checked here: being an ordinary table
    it reads without loading the sqlite-vec extension, which the audit
    process has no reason to have available.

    :param path: Candidate ``vectors.sqlite``.
    :return: True if the file is a readable SQLite database whose ``vec_meta``
        table exists and carries at least one row.
    """
    if not path.is_file():
        return False
    try:
        with contextlib.closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vec_meta'"
            ).fetchone()
            if row is None:
                return False
            return conn.execute("SELECT EXISTS(SELECT 1 FROM vec_meta)").fetchone()[0] == 1
    except sqlite3.Error:
        # Unreadable, encrypted, or not a database at all: not a usable index.
        return False


def _find_vectors(entry: KGEntry) -> Path | None:
    """Locate this KG's sqlite-vec store, if it has a usable one.

    A store that exists but holds no vectors is reported as absent, so the KG
    classifies as ``unmigrated`` and is told to convert or rebuild rather than
    to delete its LanceDB directory. See :func:`_is_populated_vector_store`.

    :param entry: The registry entry.
    :return: Path to a populated ``vectors.sqlite``, or None.
    """
    if entry.vectors_path and _is_populated_vector_store(Path(entry.vectors_path)):
        return Path(entry.vectors_path)
    default = _kg_dir(entry) / "vectors.sqlite"
    return default if _is_populated_vector_store(default) else None


def _fix_for(entry: KGEntry, status: str, lancedb_dirs: list[Path]) -> tuple[str | None, str]:
    """Return the remediation command and a short action verb for a finding.

    :param entry: The registry entry.
    :param status: The audit verdict.
    :param lancedb_dirs: LanceDB directories found on disk.
    :return: ``(command, action)``; command is None when nothing needs doing.
    """
    kind = entry.kind.value
    if status == "unmigrated":
        if kind in _DOCKG_KINDS and lancedb_dirs:
            # Paths are passed explicitly: gutenberg/ia corpora live under their
            # own marker dir, not the .dockg/ default convert-index assumes.
            vectors = _kg_dir(entry) / "vectors.sqlite"
            return (
                f"dockg convert-index --repo {shlex.quote(str(entry.repo_path))} "
                f"--lancedb {shlex.quote(str(lancedb_dirs[0]))} "
                f"--vectors-path {shlex.quote(str(vectors))} --delete-lancedb",
                "convert index",
            )
        # Everything else has no in-place converter — it has to be rebuilt.
        if kind == "code":
            return f"pycodekg build --repo {shlex.quote(str(entry.repo_path))}", "rebuild"
        return (
            f"# rebuild {kind} KG at {entry.repo_path} to produce vectors.sqlite",
            "rebuild (manual)",
        )
    if status == "residue":
        dirs = " ".join(shlex.quote(str(d)) for d in lancedb_dirs)
        return f"rm -rf {dirs}", "delete lancedb dir"
    if status == "stale-row":
        return (
            f"kgrag register {shlex.quote(entry.name)} {kind} {shlex.quote(str(entry.repo_path))}",
            "re-register",
        )
    return None, ""


def audit_entry(entry: KGEntry, *, measure: bool = True) -> LanceFinding:
    """Classify a single KG's LanceDB migration state.

    :param entry: The registry entry to audit.
    :param measure: If True, compute reclaimable disk usage (walks the tree).
    :return: A LanceFinding describing what remains.
    """
    dirs = _find_lancedb_dirs(entry)
    vectors = _find_vectors(entry)
    has_ref = entry.lancedb_path is not None

    if dirs and vectors is None:
        status = "unmigrated"
    elif dirs:
        status = "residue"
    elif has_ref:
        status = "stale-row"
    elif vectors is not None:
        status = "clean"
    else:
        status = "no-index"

    fix_cmd, action = _fix_for(entry, status, dirs)
    return LanceFinding(
        name=entry.name,
        kind=entry.kind.value,
        status=status,
        registry_reference=has_ref,
        lancedb_dirs=[str(d) for d in dirs],
        reclaimable_bytes=sum(_dir_size(d) for d in dirs) if measure else 0,
        has_vectors=vectors is not None,
        vectors_path=str(vectors) if vectors else None,
        fix_cmd=fix_cmd,
        action=action,
    )


def _fmt_mb(n: int) -> str:
    """Format a byte count as a compact MB/GB string.

    :param n: Byte count.
    :return: Human-readable size, or ``"-"`` for zero.
    """
    if n <= 0:
        return "-"
    mb = n / 1_048_576
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.1f} MB"


def _resolve_entries(
    name_or_id: str | None,
    corpus: str | None,
    kg_reg: KGRegistry,
    corpus_reg: CorpusRegistry,
) -> list[KGEntry]:
    """Resolve the audit scope to a concrete list of KG entries.

    :param name_or_id: Single KG name or UUID, or None.
    :param corpus: Corpus name to scope to, or None.
    :param kg_reg: The active KG registry.
    :param corpus_reg: The active corpus registry.
    :return: Entries to audit.
    :raises SystemExit: If a named KG or corpus does not exist.
    """
    if name_or_id:
        entry = kg_reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Not found[/red]: {name_or_id!r}")
            raise SystemExit(1)
        return [entry]
    if corpus:
        if corpus_reg.get(corpus) is None:
            console.print(f"[red]Corpus not found[/red]: {corpus!r}")
            raise SystemExit(1)
        return corpus_reg.resolve_kg_entries(corpus, kg_reg)
    return kg_reg.list()


@cli.command("audit-lancedb")
@click.argument("name_or_id", required=False, default=None)
@click.option("--corpus", "corpus", default=None, help="Audit only KGs in this corpus.")
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Include KGs that are already clean or have no vector index.",
)
@click.option(
    "--limit",
    "limit",
    type=int,
    default=20,
    show_default=True,
    help="Max KGs listed individually; 0 lists all. The rollup always covers every KG.",
)
@click.option(
    "--commands",
    "commands_only",
    is_flag=True,
    help="Print only the remediation commands, one per line (pipe to a shell).",
)
@click.option(
    "--no-sizes",
    "no_sizes",
    is_flag=True,
    help="Skip disk-usage measurement (much faster on large fleets).",
)
@click.option("--json", "output_json", is_flag=True, help="Output results as JSON.")
@registry_option
def audit_lancedb(
    name_or_id: str | None,
    corpus: str | None,
    show_all: bool,
    limit: int,
    commands_only: bool,
    no_sizes: bool,
    output_json: bool,
    registry: str | None,
) -> None:
    """Audit the registry for KGs still carrying a LanceDB index.

    Reports three kinds of LanceDB residue and how to clear each:

    \b
      unmigrated  LanceDB is still the live index (no populated
                  vectors.sqlite -- the file may be absent, or present
                  but empty from a failed migration).
                  Convert it — for doc-family KGs `dockg convert-index`
                  re-reads the stored vectors, so there is no re-embedding.
      residue     Already on sqlite-vec, but the lancedb/ dir is still
                  on disk taking space. Safe to delete.
      stale-row   The registry records a lancedb_path that no longer
                  exists. Re-register to clear the reference.

    This command only reports — it never deletes or rebuilds anything.

    \b
    Examples:
        kgrag audit-lancedb
        kgrag audit-lancedb --corpus gutenberg-all
        kgrag audit-lancedb --commands | sh
        kgrag audit-lancedb --json
    """
    db_path = Path(registry).resolve() if registry else None

    with (
        KGRegistry(db_path=db_path) as kg_reg,
        CorpusRegistry(db_path=db_path) as corpus_reg,
    ):
        entries = _resolve_entries(name_or_id, corpus, kg_reg, corpus_reg)

    findings = [audit_entry(e, measure=not no_sizes) for e in entries]
    findings.sort(key=lambda f: (_STATUS_ORDER.get(f.status, 9), f.name))

    outstanding = [f for f in findings if f.status in ("unmigrated", "residue", "stale-row")]
    reclaimable = sum(f.reclaimable_bytes for f in findings)

    if commands_only:
        for f in outstanding:
            if f.fix_cmd:
                console.print(f.fix_cmd, highlight=False, soft_wrap=True)
        return

    if output_json:
        payload = {
            "total_audited": len(findings),
            "outstanding": len(outstanding),
            "reclaimable_bytes": reclaimable,
            "by_status": {
                s: sum(1 for f in findings if f.status == s)
                for s in _STATUS_ORDER
                if any(f.status == s for f in findings)
            },
            "findings": [asdict(f) for f in findings],
        }
        console.print_json(json.dumps(payload))
        return

    shown = findings if show_all else outstanding
    if not shown:
        console.print(
            f"[green]No LanceDB residue found[/green] across {len(findings)} KG(s). "
            "The fleet is sqlite-vec only."
        )
        return

    # --- rollup: the useful view when hundreds of corpora share one problem ---
    roll = Table(title="LanceDB Audit — by kind", box=box.ROUNDED)
    roll.add_column("Kind", style="magenta")
    roll.add_column("Status")
    roll.add_column("KGs", justify="right")
    roll.add_column("On disk", justify="right")

    groups: dict[tuple[str, str], list[LanceFinding]] = {}
    for f in shown:
        groups.setdefault((f.kind, f.status), []).append(f)
    for (kind, status), group in sorted(
        groups.items(), key=lambda kv: (_STATUS_ORDER.get(kv[0][1], 9), kv[0][0])
    ):
        style = _STATUS_STYLE.get(status, "")
        size = sum(g.reclaimable_bytes for g in group)
        roll.add_row(
            kind,
            f"[{style}]{status}[/{style}]",
            str(len(group)),
            _fmt_mb(size) if not no_sizes else "[dim]n/a[/dim]",
        )
    console.print(roll)

    # --- bounded per-KG detail ---
    cap = len(shown) if limit == 0 else min(limit, len(shown))
    if cap:
        table = Table(
            title=f"Affected KGs ({cap} of {len(shown)})", box=box.ROUNDED, show_lines=False
        )
        table.add_column("Name", style="bold cyan", max_width=44, no_wrap=False)
        table.add_column("Kind", style="magenta", width=10)
        table.add_column("Status", width=11)
        table.add_column("Vectors", justify="center", width=7)
        table.add_column("On disk", justify="right", width=9)
        table.add_column("Action", width=19)

        for f in shown[:cap]:
            style = _STATUS_STYLE.get(f.status, "")
            table.add_row(
                f.name,
                f.kind,
                f"[{style}]{f.status}[/{style}]",
                "[green]yes[/green]" if f.has_vectors else "[red]no[/red]",
                _fmt_mb(f.reclaimable_bytes) if not no_sizes else "[dim]n/a[/dim]",
                f.action or "—",
            )
        console.print(table)
        if cap < len(shown):
            console.print(
                f"[dim]… and {len(shown) - cap} more not shown "
                f"(use --limit 0 for the full list).[/dim]"
            )

    counts = {s: sum(1 for f in findings if f.status == s) for s in _STATUS_ORDER}
    summary = "  ".join(
        f"[{_STATUS_STYLE.get(s, '')}]{s}[/{_STATUS_STYLE.get(s, '')}]: {n}"
        for s, n in counts.items()
        if n
    )
    console.print(f"\n[bold]Audited[/bold] {len(findings)} KG(s)   {summary}")
    if no_sizes:
        console.print("[dim]Disk usage not measured (--no-sizes).[/dim]")
    elif reclaimable:
        console.print(f"[bold]Reclaimable[/bold] {_fmt_mb(reclaimable)} of LanceDB data on disk")
    for status, n in counts.items():
        if n and status in _STATUS_ACTION:
            console.print(f"  [dim]{status:11s} {_STATUS_BLURB[status]}[/dim]")
    if outstanding:
        console.print(
            "\n[dim]Run [bold]kgrag audit-lancedb --commands[/bold] to emit just the "
            "fix commands. Review them before running — conversions rewrite indices "
            "and `rm -rf` deletes data.[/dim]"
        )
