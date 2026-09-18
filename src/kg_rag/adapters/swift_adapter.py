"""swift_adapter.py -- KGAdapter for SwiftKG.

Wraps ``swift_kg.SwiftKG``, the Swift port of PyCodeKG, through the shared
:class:`~kg_rag.adapters._code_module_adapter.CodeModuleKGAdapter`.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from kg_rag.adapters._code_module_adapter import CodeModuleKGAdapter
from kg_rag.primitives import KGKind


class SwiftKGAdapter(CodeModuleKGAdapter):
    """Adapter for SwiftKG (Swift code knowledge graphs).

    :param entry: KGEntry with ``kind=KGKind.SWIFT``.
    """

    kg_kind = KGKind.SWIFT
    module_name = "swift_kg"
    class_name = "SwiftKG"
    dist_name = "swift-kg"
    store_dir = ".swiftkg"
