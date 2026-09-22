"""vault_adapter.py -- KGAdapter for VaultKG.

Wraps ``vaultkg.VaultKG``: an Obsidian-style Markdown vault whose graph is its
own wikilinks, embeds, headings, tags and typed links, parsed rather than
extracted by a model. VaultKG subclasses ``kg_utils.pipeline.KGModule`` with
the constructor and node shape the code modules use (score under
``relevance``, source span under ``snippet``), so it rides the shared
:class:`~kg_rag.adapters._code_module_adapter.CodeModuleKGAdapter`.

Notes carry the fleet temporal keys when their frontmatter has ``date`` or
``created``, and every hit passes its node metadata through, so a
``time_range`` scope post-filters vault hits like any dated backend's.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters._code_module_adapter import CodeModuleKGAdapter
from kg_rag.primitives import KGKind


class VaultKGAdapter(CodeModuleKGAdapter):
    """Adapter for VaultKG (Markdown / Obsidian vault knowledge graphs).

    :param entry: KGEntry with ``kind=KGKind.VAULT``.
    """

    kg_kind = KGKind.VAULT
    module_name = "vaultkg"
    class_name = "VaultKG"
    dist_name = "vault-kg"
    store_dir = ".vaultkg"

    def stats(self) -> dict[str, Any]:
        """Standard envelope plus note, heading, tag and unresolved-link counts.

        :return: The shared envelope from the base adapter, with vault counts.
        """
        s = super().stats()
        if "error" in s:
            return s
        try:
            raw = self._kg.stats()
        except Exception:  # pylint: disable=broad-exception-caught
            return s
        s.pop("docstring_coverage", None)  # a code-graph figure; always 0 here
        for key in ("notes", "headings", "tags", "unresolved"):
            s[key] = raw.get(key, 0)
        return s
