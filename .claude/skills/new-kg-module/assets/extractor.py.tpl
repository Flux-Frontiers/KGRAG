"""
{{name}}/extractor.py

{{ExtractorName}} — KGExtractor for {{name}}.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from code_kg.module import EdgeSpec, KGExtractor, NodeSpec


class {{ExtractorName}}(KGExtractor):
    """Extract nodes and edges from {{name}} sources.

    :param repo_path: Absolute path to the repository or corpus root.
    :param config: Optional domain-specific configuration dict.
    """

    def __init__(self, repo_path: Path, config: dict[str, Any] | None = None) -> None:
        super().__init__(repo_path, config)

    def node_kinds(self) -> list[str]:
        """Return canonical node kind names.

        :return: {{node_kinds}}
        """
        return {{node_kinds}}

    def edge_kinds(self) -> list[str]:
        """Return canonical edge relation types.

        :return: {{edge_kinds}}
        """
        return {{edge_kinds}}

    def meaningful_node_kinds(self) -> list[str]:
        """Return node kinds included in the vector index and coverage metrics.

        Override to exclude structural stubs from the default (all node_kinds).

        :return: Subset of node_kinds() to index semantically.
        """
        return self.node_kinds()

    def coverage_metric(self, nodes: list[NodeSpec]) -> float:
        """Compute a domain coverage quality metric for snapshots.

        Default: fraction of meaningful nodes with a non-empty docstring.
        Override with a domain-appropriate signal.

        :param nodes: All extracted NodeSpec objects.
        :return: Coverage score in [0.0, 1.0].
        """
        meaningful = [n for n in nodes if n.kind in self.meaningful_node_kinds()]
        if not meaningful:
            return 0.0
        covered = sum(1 for n in meaningful if n.docstring.strip())
        return covered / len(meaningful)

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        """Traverse the source and yield NodeSpec / EdgeSpec objects.

        node_id format: '<kind>:<source_path>:<qualname>'

        :return: Iterator of NodeSpec and EdgeSpec objects.
        """
        # TODO: implement domain-specific extraction
        # Example pattern:
        #
        # for source in self.repo_path.rglob("*"):
        #     yield NodeSpec(
        #         node_id=f"<kind>:{source.relative_to(self.repo_path)}:<qualname>",
        #         kind="<kind>",
        #         name=source.name,
        #         qualname=str(source.relative_to(self.repo_path)),
        #         source_path=str(source.relative_to(self.repo_path)),
        #         docstring="",
        #     )
        #     yield EdgeSpec(
        #         source_id="<parent_id>",
        #         target_id=f"<kind>:{source.relative_to(self.repo_path)}:<qualname>",
        #         relation="CONTAINS",
        #     )
        raise NotImplementedError
