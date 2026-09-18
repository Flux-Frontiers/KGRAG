"""typescript_adapter.py -- KGAdapter for TypeScriptKG.

Wraps ``tscode_kg.TypeScriptKG``, the TypeScript/JavaScript port of PyCodeKG,
through the shared
:class:`~kg_rag.adapters._code_module_adapter.CodeModuleKGAdapter`.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from kg_rag.adapters._code_module_adapter import CodeModuleKGAdapter
from kg_rag.primitives import KGKind


class TypeScriptKGAdapter(CodeModuleKGAdapter):
    """Adapter for TypeScriptKG (TypeScript/JavaScript code knowledge graphs).

    :param entry: KGEntry with ``kind=KGKind.TYPESCRIPT``.
    """

    kg_kind = KGKind.TYPESCRIPT
    module_name = "tscode_kg"
    class_name = "TypeScriptKG"
    dist_name = "tscode-kg"
    store_dir = ".tscodekg"
