"""
cmd_health.py

Full-stack health check for the KGRAG registry.

Reports issues across all registered KGs and corpora with suggested
remediation commands.  With ``--fix`` it auto-repairs issues that can
be resolved without a long-running build (dangling corpus refs, entries
whose repo path has disappeared).

Usage::

    kgrag health               # report all issues + suggested fix commands
    kgrag health --fix         # auto-repair fixable issues, print the rest
    kgrag health --json        # machine-readable JSON output
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.registry import KGRegistry

console = Console()

# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "warning": 1, "info": 2}
_SEVERITY_STYLE: dict[str, str] = {
    "critical": "bold red",
    "warning": "yellow",
    "info": "dim",
}
_SEVERITY_ICON: dict[str, str] = {"critical": "✖", "warning": "⚠", "info": "·"}

# ---------------------------------------------------------------------------
# Build-command templates  (kind → shell command template)
# ---------------------------------------------------------------------------

_BUILD_CMD_TPL: dict[str, str] = {
    "code": "codekg build --repo {repo}",
    "doc": "dockg build --repo {repo}",
    "memory": "memorykg-build --repo {repo}",
    "diary": "diarykg build --repo {repo}",
    "meta": "# metabokg build  (check metabokg CLI for exact command)",
    "verse": "versekg build --repo {repo}",
    "disulfide": "disulfidekg build --repo {repo}",
    "pdbfile": "pdbfilekg build --repo {repo}",
    "legal": "legalkg build --repo {repo}",
    "person": "personkg build --repo {repo}",
    "agent": "# agentkg is live — no manual build needed",
}


def _build_cmd(kind: str, repo: Path) -> str:
    """Return the build command for a given KG kind and repo path.

    :param kind: KG kind string (e.g. ``"code"``).
    :param repo: Absolute path to the repository root.
    :return: Shell command string.
    """
    tpl = _BUILD_CMD_TPL.get(kind, "# {kind}kg build --repo {repo}  (check docs)")
    return tpl.format(repo=repo, kind=kind)


# ---------------------------------------------------------------------------
# Issue model
# ---------------------------------------------------------------------------


@dataclass
class HealthIssue:
    """A single issue found during the health check.

    :param severity: ``"critical"`` | ``"warning"`` | ``"info"``.
    :param check: Machine-readable check identifier.
    :param target: Name of the affected KG or corpus.
    :param message: Human-readable description.
    :param fix_cmd: Suggested CLI command, or ``None``.
    :param auto_fixable: True if ``--fix`` can repair this programmatically.
    """

    severity: str
    check: str
    target: str
    message: str
    fix_cmd: str | None
    auto_fixable: bool


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def _check_kgs(entries: list, issues: list[HealthIssue]) -> None:
    """Inspect every registered KG entry and append issues found.

    :param entries: List of KGEntry objects from the registry.
    :param issues: Mutable list to append HealthIssue objects into.
    """
    for e in entries:
        # --- repo path missing on disk ---
        if not e.repo_path.exists():
            issues.append(
                HealthIssue(
                    severity="critical",
                    check="missing_repo",
                    target=e.name,
                    message=f"repo_path does not exist: {e.repo_path}",
                    fix_cmd=f"kgrag unregister {e.name}",
                    auto_fixable=True,
                )
            )
            continue  # further checks pointless without the repo

        # --- index not built ---
        if not e.is_built:
            issues.append(
                HealthIssue(
                    severity="warning",
                    check="unbuilt",
                    target=e.name,
                    message=f"No built index found (kind={e.kind.value})",
                    fix_cmd=_build_cmd(e.kind.value, e.repo_path),
                    auto_fixable=False,
                )
            )
            continue  # stale-path checks not meaningful when nothing is built

        # --- SQLite registered but file missing ---
        if e.sqlite_path and not Path(e.sqlite_path).exists():
            issues.append(
                HealthIssue(
                    severity="warning",
                    check="stale_sqlite",
                    target=e.name,
                    message=f"SQLite registered but file missing: {e.sqlite_path}",
                    fix_cmd=_build_cmd(e.kind.value, e.repo_path),
                    auto_fixable=False,
                )
            )

        # --- LanceDB registered but directory missing ---
        if e.lancedb_path and not Path(e.lancedb_path).exists():
            issues.append(
                HealthIssue(
                    severity="warning",
                    check="stale_lancedb",
                    target=e.name,
                    message=f"LanceDB registered but directory missing: {e.lancedb_path}",
                    fix_cmd=_build_cmd(e.kind.value, e.repo_path),
                    auto_fixable=False,
                )
            )


def _check_corpora(
    corpora: list,
    kg_reg: KGRegistry,
    issues: list[HealthIssue],
) -> None:
    """Inspect every corpus for broken references and unbuilt members.

    :param corpora: List of CorpusEntry objects.
    :param kg_reg: The active KGRegistry instance.
    :param issues: Mutable list to append HealthIssue objects into.
    """
    kg_by_id = {e.id: e for e in kg_reg.list()}

    for corpus in corpora:
        for kg_id in corpus.kg_ids:
            if kg_id not in kg_by_id:
                issues.append(
                    HealthIssue(
                        severity="warning",
                        check="corpus_broken_ref",
                        target=corpus.name,
                        message=f"Member KG id {kg_id!r} not found in registry",
                        fix_cmd=f"kgrag corpus remove {corpus.name} {kg_id}",
                        auto_fixable=True,
                    )
                )
            else:
                entry = kg_by_id[kg_id]
                if not entry.is_built:
                    issues.append(
                        HealthIssue(
                            severity="warning",
                            check="corpus_unbuilt_member",
                            target=corpus.name,
                            message=(f"Member '{entry.name}' ({entry.kind.value}) is not built"),
                            fix_cmd=_build_cmd(entry.kind.value, entry.repo_path),
                            auto_fixable=False,
                        )
                    )


# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------


def _apply_fixes(
    issues: list[HealthIssue],
    kg_reg: KGRegistry,
    corpus_reg: CorpusRegistry,
) -> tuple[list[HealthIssue], list[str]]:
    """Apply auto-fixable repairs and return remaining issues and a fix log.

    :param issues: All detected issues.
    :param kg_reg: Open KGRegistry for write operations.
    :param corpus_reg: Open CorpusRegistry for write operations.
    :return: Tuple of (remaining_issues, fix_log_messages).
    """
    remaining: list[HealthIssue] = []
    log: list[str] = []

    for issue in issues:
        if not issue.auto_fixable:
            remaining.append(issue)
            continue

        if issue.check == "missing_repo":
            if click.confirm(
                f"  Unregister '{issue.target}' (repo path no longer exists)?",
                default=False,
            ):
                kg_reg.unregister(issue.target)
                log.append(f"Unregistered '{issue.target}' (missing repo path)")
            else:
                remaining.append(issue)

        elif issue.check == "corpus_broken_ref":
            # fix_cmd format: "kgrag corpus remove <corpus> <kg_id>"
            parts = (issue.fix_cmd or "").split()
            if len(parts) == 5:
                kg_id = parts[-1]
                corpus_reg.remove_kg(issue.target, kg_id)
                log.append(f"Removed dangling ref {kg_id!r} from corpus '{issue.target}'")
            else:
                remaining.append(issue)

        else:
            remaining.append(issue)

    return remaining, log


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@cli.command("health")
@click.option(
    "--fix",
    "do_fix",
    is_flag=True,
    help="Auto-repair fixable issues (broken corpus refs, missing repos with confirmation).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON instead of a Rich table.",
)
@registry_option
def health(do_fix: bool, output_json: bool, registry: str | None) -> None:
    """Full-stack health check for the KGRAG registry.

    Inspects all registered KGs and corpora for common issues:

    \b
      • unbuilt indices
      • repo paths that no longer exist on disk
      • SQLite / LanceDB paths registered but files missing
      • broken corpus member references (KG removed from registry but
        still referenced in a corpus)
      • corpus members that haven't been built yet

    \b
    Without --fix: reports all issues with suggested remediation commands.
    With    --fix: auto-repairs fixable issues (removes dangling corpus
                   refs; offers to unregister KGs with missing repos)
                   and prints manual-step commands for the rest.

    \b
    Examples:
        kgrag health
        kgrag health --fix
        kgrag health --json
    """
    db_path = Path(registry).resolve() if registry else None

    with (
        KGRegistry(db_path=db_path) as kg_reg,
        CorpusRegistry(db_path=db_path) as corpus_reg,
    ):
        entries = kg_reg.list()
        corpora = corpus_reg.list()
        reg_path = kg_reg.db_path

        issues: list[HealthIssue] = []
        _check_kgs(entries, issues)
        _check_corpora(corpora, kg_reg, issues)

        # Sort: critical first, then by target name
        issues.sort(key=lambda i: (_SEVERITY_ORDER.get(i.severity, 9), i.target))

        fix_log: list[str] = []
        if do_fix and issues:
            if not output_json:
                console.print("\n[bold]Applying auto-repairs…[/bold]")
            issues, fix_log = _apply_fixes(issues, kg_reg, corpus_reg)
            if not output_json:
                for msg in fix_log:
                    console.print(f"  [green]fixed[/green]  {msg}")

    # -----------------------------------------------------------------------
    # JSON output
    # -----------------------------------------------------------------------
    if output_json:
        out = {
            "registry": str(reg_path),
            "total_kgs": len(entries),
            "total_corpora": len(corpora),
            "issues": [asdict(i) for i in issues],
            "fixed": fix_log,
        }
        console.print_json(json.dumps(out, indent=2))
        return

    # -----------------------------------------------------------------------
    # Rich output
    # -----------------------------------------------------------------------
    n_critical = sum(1 for i in issues if i.severity == "critical")
    n_warning = sum(1 for i in issues if i.severity == "warning")
    n_built = sum(1 for e in entries if e.is_built)

    if not issues:
        status_line = "[bold green]✔  All checks passed — stack is healthy[/bold green]"
    elif n_critical:
        status_line = f"[bold red]✖  {n_critical} critical  {n_warning} warning(s)[/bold red]"
    else:
        status_line = f"[bold yellow]⚠  {n_warning} warning(s)[/bold yellow]"

    console.print(
        Panel(
            f"[bold]Registry :[/bold] {reg_path}\n"
            f"[bold]KGs      :[/bold] {len(entries)} registered  "
            f"({n_built} built, {len(entries) - n_built} unbuilt)\n"
            f"[bold]Corpora  :[/bold] {len(corpora)}\n"
            f"\n{status_line}",
            title="[bold]KGRAG Health Check[/bold]",
            expand=False,
        )
    )

    if not issues:
        return

    # Issues table
    table = Table(box=box.ROUNDED, show_lines=False, title="Issues Found")
    table.add_column("", justify="center", width=2, no_wrap=True)
    table.add_column("Check", style="bold", width=24, no_wrap=True)
    table.add_column("Target", style="cyan", width=32, no_wrap=True)
    table.add_column("Description")
    table.add_column("Fix", justify="center", width=6, no_wrap=True)

    for issue in issues:
        sev_style = _SEVERITY_STYLE.get(issue.severity, "")
        sev_icon = _SEVERITY_ICON.get(issue.severity, "?")
        fix_label = Text("auto", style="green") if issue.auto_fixable else Text("cmd", style="dim")
        table.add_row(
            Text(sev_icon, style=sev_style),
            Text(issue.check, style=sev_style),
            issue.target,
            issue.message,
            fix_label,
        )

    console.print(table)

    # Suggested commands for non-auto-fixable issues
    cmds = [(i.target, i.fix_cmd) for i in issues if i.fix_cmd and not i.auto_fixable]
    if cmds:
        console.print("\n[bold]Suggested fix commands:[/bold]")
        seen: set[str] = set()
        for target, cmd in cmds:
            if cmd not in seen:
                console.print(f"  [dim]# {target}[/dim]")
                console.print(f"  [cyan]{cmd}[/cyan]")
                seen.add(cmd)

    # Nudge toward --fix when auto-fixable issues exist
    auto_count = sum(1 for i in issues if i.auto_fixable)
    if not do_fix and auto_count:
        console.print(
            f"\n[dim]{auto_count} issue(s) can be auto-repaired — "
            "run [bold]kgrag health --fix[/bold] to apply.[/dim]"
        )
