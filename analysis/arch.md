ℹ️  Tip: Run 'codekg analyze --json' then 'codekg architecture --load-latest'
    for richer architectural insights.
# Overview

> **Generated:** 2026-03-14T17:47:40.797577+00:00 | **Version:** 0.8.1 | **Commit:** fc7533c541

This codebase is organized into 1 architectural layers: Src Layer. The architecture supports semantic code search via knowledge graph indexing and querying.

## Architectural Layers

### Src Layer
Handles src concerns.

**Responsibilities:**
- Component responsibility

**Modules:**
- `src/kg_rag/__init__.py`
- `src/kg_rag/adapters/__init__.py`
- `src/kg_rag/adapters/base.py`
- `src/kg_rag/adapters/codekg_adapter.py`
- `src/kg_rag/adapters/dockg_adapter.py`
- `src/kg_rag/adapters/metakg_adapter.py`
- `src/kg_rag/app.py`
- `src/kg_rag/cli/__init__.py`
- `src/kg_rag/cli/cmd_analyze.py`
- `src/kg_rag/cli/cmd_init.py`
- `src/kg_rag/cli/cmd_mcp.py`
- `src/kg_rag/cli/cmd_query.py`
- `src/kg_rag/cli/cmd_registry.py`
- `src/kg_rag/cli/cmd_viz.py`
- `src/kg_rag/cli/group.py`
- `src/kg_rag/cli/main.py`
- `src/kg_rag/cli/options.py`
- `src/kg_rag/config.py`
- `src/kg_rag/mcp_server.py`
- `src/kg_rag/orchestrator.py`
- `src/kg_rag/primitives.py`
- `src/kg_rag/registry.py`

## Key Components

### KGAdapter
**Type:** `class` | **File:** `src/kg_rag/adapters/base.py:15`

Abstract base for KG adapters (CodeKG, DocKG, MetaKG).

### CodeKGAdapter
**Type:** `class` | **File:** `src/kg_rag/adapters/codekg_adapter.py:15`

Adapter for CodeKG (Python code knowledge graphs).

### DocKGAdapter
**Type:** `class` | **File:** `src/kg_rag/adapters/dockg_adapter.py:15`

Adapter for DocKG (document/markdown knowledge graphs).

### MetaKGAdapter
**Type:** `class` | **File:** `src/kg_rag/adapters/metakg_adapter.py:15`

Adapter for MetaKG (metabolic pathway knowledge graphs).

### KGRAG
**Type:** `class` | **File:** `src/kg_rag/orchestrator.py:27`

Cross-KG orchestrator: query multiple KG instances as a unified corpus.

## Critical Paths

### Path 1: Graph Query Pipeline
Semantic search → graph expansion → snippet packing

- Semantic search finds seed nodes via LanceDB
- Graph expansion traverses CALLS, CONTAINS, IMPORTS edges
- Snippet pack materializes source code with context

### Path 2: AST Extraction & Graph Building
Repository scanning → code analysis → graph storage

- CodeGraph walks repo and extracts Python files
- CodeKGVisitor traverses AST, collects nodes and edges
- GraphStore persists in SQLite with symbol resolution

## Dependency & Coupling Analysis

### Module Dependencies
**src/kg_rag/config.py**
- imports: __future__.annotations
- imports: pathlib.Path

**src/kg_rag/primitives.py**
- imports: __future__.annotations
- imports: uuid
- imports: dataclasses.dataclass
- imports: dataclasses.field
- imports: datetime.UTC
- imports: datetime.datetime
- imports: enum.Enum
- imports: pathlib.Path
- imports: typing.Any

**src/kg_rag/registry.py**
- imports: __future__.annotations
- imports: json
- imports: os
- imports: sqlite3
- imports: datetime.UTC
- imports: datetime.datetime
- imports: pathlib.Path
- imports: typing.Iterator
- imports: kg_rag.primitives.KGEntry
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.primitives.RegistryStats

**src/kg_rag/__init__.py**
- imports: kg_rag.orchestrator.KGRAG
- imports: kg_rag.primitives.CrossHit
- imports: kg_rag.primitives.CrossQueryResult
- imports: kg_rag.primitives.CrossSnippet
- imports: kg_rag.primitives.CrossSnippetPack
- imports: kg_rag.primitives.KGEntry
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.primitives.RegistryStats
- imports: kg_rag.registry.KGRegistry

**src/kg_rag/orchestrator.py**
- imports: __future__.annotations
- imports: pathlib.Path
- imports: typing.Sequence
- imports: kg_rag.adapters.KGAdapter
- imports: kg_rag.adapters.make_adapter
- imports: kg_rag.primitives.CrossHit
- imports: kg_rag.primitives.CrossQueryResult
- imports: kg_rag.primitives.CrossSnippet
- imports: kg_rag.primitives.CrossSnippetPack
- imports: kg_rag.primitives.KGEntry
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.registry.KGRegistry

**src/kg_rag/app.py**
- imports: __future__.annotations
- imports: json
- imports: os
- imports: pathlib.Path
- imports: streamlit
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.registry.default_registry_path

**src/kg_rag/mcp_server.py**
- imports: __future__.annotations
- imports: asyncio
- imports: json
- imports: pathlib.Path
- imports: typing.Any
- imports: mcp.server.Server
- imports: mcp.server.stdio.stdio_server
- imports: mcp.types.TextContent
- imports: mcp.types.Tool
- imports: kg_rag.orchestrator.KGRAG
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.registry.KGRegistry
- imports: kg_rag.registry.default_registry_path

**src/kg_rag/cli/options.py**
- imports: __future__.annotations
- imports: click

**src/kg_rag/cli/cmd_viz.py**
- imports: __future__.annotations
- imports: importlib.util
- imports: subprocess
- imports: sys
- imports: pathlib.Path
- imports: click
- imports: kg_rag.cli.group.cli

**src/kg_rag/cli/cmd_registry.py**
- imports: __future__.annotations
- imports: os
- imports: datetime.date
- imports: pathlib.Path
- imports: click
- imports: rich.box
- imports: rich.console.Console
- imports: rich.panel.Panel
- imports: rich.table.Table
- imports: kg_rag.cli.group.cli
- imports: kg_rag.cli.options.kind_option
- imports: kg_rag.cli.options.registry_option
- imports: kg_rag.config.read_pyproject_version
- imports: kg_rag.primitives.KGEntry
- imports: kg_rag.primitives.KGKind
- imports: kg_rag.registry.KGRegistry
- imports: kg_rag.registry.default_registry_path

**src/kg_rag/cli/cmd_mcp.py**
- imports: __future__.annotations
- imports: pathlib.Path
- imports: click
- imports: kg_rag.cli.group.cli
- imports: kg_rag.cli.options.registry_option

**src/kg_rag/cli/__init__.py**
- imports: kg_rag.cli.main.cli

**src/kg_rag/cli/cmd_query.py**
- imports: __future__.annotations
- imports: pathlib.Path
- imports: click
- imports: rich.console.Console
- imports: rich.table.Table

## Health & Quality Signals

- **Circular Dependencies:** 0
- **Coupling Health:** ✅ Acyclic
- **Orphaned Functions:** 0
- **Dead Code Status:** ✅ Clean

