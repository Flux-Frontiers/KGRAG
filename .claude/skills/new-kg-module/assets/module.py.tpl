"""
{{name}}/module.py

{{ClassName}} — KGModule for {{name}}.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from code_kg.module import KGModule

from {{name}}.extractor import {{ExtractorName}}


class {{ClassName}}(KGModule):
    """Knowledge graph module for {{name}}.

    Provides build, query, pack, analyze, and snapshot operations
    over {{name}} sources using the KGModule infrastructure.

    :param repo_root: Absolute path to the repository or corpus root.
    :param db_path: Path for the SQLite graph database.
    :param lancedb_path: Path for the LanceDB vector index directory.
    :param config: Optional domain-specific configuration dict.
    """

    def __init__(
        self,
        repo_root: Path | str,
        db_path: Path | str | None = None,
        lancedb_path: Path | str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        repo_root = Path(repo_root).resolve()
        db_path = Path(db_path) if db_path else repo_root / ".{{name}}" / "graph.sqlite"
        lancedb_path = Path(lancedb_path) if lancedb_path else repo_root / ".{{name}}" / "lancedb"
        super().__init__(repo_root=repo_root, db_path=db_path, lancedb_path=lancedb_path, config=config)

    def make_extractor(self) -> {{ExtractorName}}:
        """Return the domain extractor for this module.

        :return: {{ExtractorName}} instance.
        """
        return {{ExtractorName}}(self.repo_root, self.config)

    def kind(self) -> str:
        """Return the KGKind string for this module.

        :return: "{{kg_kind}}"
        """
        return "{{kg_kind}}"

    def analyze(self) -> str:
        """Run full analysis and return a Markdown report.

        :return: Markdown-formatted analysis report.
        """
        try:
            s = self.stats()
            lines = [
                "# {{ClassName}} Analysis",
                "",
                f"**Nodes:** {s.node_count}  ",
                f"**Edges:** {s.edge_count}  ",
                "",
                "## Node breakdown",
                "",
            ]
            for kind, count in (s.node_counts or {}).items():
                lines.append(f"- `{kind}`: {count}")
            lines += ["", "## Edge breakdown", ""]
            for rel, count in (s.edge_counts or {}).items():
                lines.append(f"- `{rel}`: {count}")
            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# {{ClassName}} Analysis\n\nAnalysis failed: {exc}\n"
