# CodeKG Query Cheatsheet

A practical reference for the ten MCP tools, with examples drawn from this codebase.
All queries below work against the live `code_kg` knowledge graph.

---

## The Ten Tools at a Glance

| Tool | Best for | Returns |
|---|---|---|
| `graph_stats()` | Orientation — size and shape of the graph | JSON: node/edge counts by kind |
| `query_codebase(q)` | Structural exploration — *what exists, how things relate* | JSON: ranked nodes + edges |
| `pack_snippets(q)` | Implementation detail — *actual source code* | Markdown: snippets with line numbers |
| `get_node(node_id, include_edges)` | Pinpoint lookup — one node by its stable ID + optional neighborhood | JSON: full node metadata |
| `list_nodes(module_path, kind)` | Enumerate module contents — *what classes/functions are in this file?* | JSON: array of matching node dicts |
| `callers(node_id, rel)` | Fan-in lookup — *who calls this function?* | JSON: all caller nodes, resolved through stubs |
| `explain(node_id)` | Natural language understanding — *what does this do?* | Markdown: role, callers, callees, docstring |
| `analyze_repo()` | Full architectural health check — complexity, coupling, orphans | Markdown: nine-phase analysis |
| `snapshot_list(limit)` | Temporal tracking — *how has the codebase grown?* | JSON: snapshots with deltas, newest first |
| `snapshot_show(key)` | Snapshot detail — full metrics at a specific snapshot key (tree hash) or `"latest"` | JSON: full metrics + hotspots + deltas |
| `snapshot_diff(key_a, key_b)` | Before/after comparison — *what changed between two snapshots?* | JSON: metrics for both + computed delta |

---

## 1. Orient First with `graph_stats`

Always start here when approaching an unfamiliar codebase or after a rebuild.

```python
graph_stats()
```

Returns counts broken down by node kind and edge relation.
For this repo you'll see:

```json
{
  "total_nodes": 3093,
  "total_edges": 2534,
  "node_counts": { "class": 17, "function": 209, "method": 80, "module": 21, "symbol": 2766 },
  "edge_counts": { "ATTR_ACCESS": 945, "CALLS": 1114, "CONTAINS": 306, "IMPORTS": 165, "INHERITS": 4 }
}
```

High symbol counts mean data-flow edges are active (ATTR_ACCESS, READS, WRITES). High CALLS counts mean the call graph is rich.

---

## 2. Semantic Exploration with `query_codebase`

Returns a ranked set of nodes and the edges between them. Good for mapping unknown territory.

### Find classes and their methods

```python
query_codebase("knowledge graph storage persistence")
```

Returns `GraphStore`, `CodeKG`, and the edges connecting them — no need to know filenames.

### Trace a call chain

```python
query_codebase("query pipeline semantic search expansion", rels="CALLS")
```

`rels=` restricts graph expansion to a single edge type. Set it to `"CALLS"` to follow execution flow only.

### Explore the module import graph

```python
query_codebase("module imports dependencies", rels="IMPORTS")
```

### Find inheritance hierarchies

```python
query_codebase("NodeVisitor AST visitor base class", rels="INHERITS")
```

`CodeKGVisitor` inherits from `ast.NodeVisitor` — this surfaces that relationship.

### Combine edge types

```python
query_codebase("build index embedding", rels="CALLS,IMPORTS")
```

Comma-separated `rels` expand through multiple relation types simultaneously.

### Increase graph depth

```python
query_codebase("error handling exception", hop=2)
```

`hop=2` follows edges two levels out from each seed. Useful when the entry point is one hop away from the interesting logic.

### Include symbol-level nodes

```python
query_codebase("self.edges attribute access", include_symbols=True)
```

With `include_symbols=True` the result includes `symbol` nodes — per-scope variable and attribute references created by `CodeKGVisitor`.

---

## 3. Source Retrieval with `pack_snippets`

Returns Markdown with actual source snippets, ranked and deduplicated. Use this when you need to *read* the code, not just locate it.

### Understand an implementation

```python
pack_snippets("visitor scope tracking variable assignment")
```

Returns `CodeKGVisitor`, `visit_FunctionDef`, `visit_Assign` with surrounding source lines.

### Get context for a specific concept

```python
pack_snippets("graph expansion hop traversal", max_nodes=5)
```

`max_nodes` limits the number of snippets returned — useful when you only need the top results.

### Widen the snippet window

```python
pack_snippets("schema SQL CREATE TABLE", context=15)
```

`context=` controls how many lines of context appear above and below each definition. Default is 5; raise it for dense logic.

### Cap snippet length

```python
pack_snippets("to_markdown render output", max_lines=40)
```

`max_lines=` prevents very long functions from dominating the output.

### Increase semantic seeds

```python
pack_snippets("embedding model LanceDB index build", k=12)
```

`k=` is the number of semantic seed nodes before graph expansion. Raise it when the first results feel off-target.

---

## 4. Pinpoint Lookup with `get_node`

Fetch a single node by its stable ID. Node IDs appear in `query_codebase` and `pack_snippets` results.
Pass `include_edges=True` to retrieve outgoing edges and incoming callers in the same call.

### Node ID format

```
<kind>:<module_path>:<qualname>

fn:src/code_kg/mcp_server.py:pack_snippets
m:src/code_kg/visitor.py:CodeKGVisitor.visit_Attribute
cls:src/code_kg/store.py:GraphStore
mod:src/code_kg/kg.py
```

### Fetch a function

```python
get_node("fn:src/code_kg/mcp_server.py:query_codebase")
```

Returns `lineno`, `end_lineno`, `docstring`, `module_path`, `qualname`.

### Fetch with immediate neighborhood

```python
get_node("fn:src/code_kg/mcp_server.py:query_codebase", include_edges=True)
```

Also returns `outgoing_edges` (grouped by CALLS, CONTAINS, IMPORTS, INHERITS) and `incoming_calls`.
Eliminates a separate `callers()` call for routine inspection.

### Fetch a method

```python
get_node("m:src/code_kg/visitor.py:CodeKGVisitor.finalize")
```

### Fetch a module

```python
get_node("mod:src/code_kg/__init__.py")
```

### List nodes in a module

```python
list_nodes("src/code_kg/store.py", kind="class")
```

Returns all classes defined in `store.py`. Omit `kind` to get functions and methods too.

---

## 5. Fan-In Lookup with `callers`

Find all nodes that call a given function, including cross-module callers resolved through symbol stubs.

### Find direct and indirect callers

```python
callers("fn:src/code_kg/store.py:GraphStore.expand")
```

Returns all functions that call `expand()`, with full node metadata (location, docstring, etc.).

### Restrict by relation type

```python
callers("fn:src/code_kg/store.py:GraphStore.expand", rel="CALLS")
```

Use `rel="INHERITS"` to find all subclasses, `rel="IMPORTS"` to find all importers.

---

## 6. Natural-Language Explanation with `explain`

```python
explain("fn:src/code_kg/store.py:GraphStore.expand")
explain("m:src/code_kg/visitor.py:CodeKGVisitor.visit_FunctionDef")
explain("cls:src/code_kg/store.py:GraphStore")
```

Returns: role assessment, module path + line range, full docstring, callers (top 10), callees.
Use before `pack_snippets` when you want to understand a node's purpose before reading its source.

---

## 7. Temporal Tracking with Snapshot Tools

```python
snapshot_list()               # 10 most recent snapshots, newest first
snapshot_list(limit=0)        # all snapshots
snapshot_show()               # most recent snapshot (full metrics + hotspots + deltas)
snapshot_show("abc1234")      # specific commit hash
snapshot_diff("abc1234", "def5678")   # compare two commits (delta: nodes, edges, coverage)
```

Snapshots are captured by the post-commit hook (`codekg install-hooks`), stored in `.codekg/snapshots/`.

---

## 9. Data-Flow Queries (from `CodeKGVisitor`)

The `CodeKGVisitor` class enriches the graph with **data-flow** edges.
These enable a new category of query that structural tools (CALLS, CONTAINS) cannot answer.

### ATTR_ACCESS — attribute access patterns

`ATTR_ACCESS` edges connect a variable node to the attribute being accessed on it.
Pattern: `scope.obj` →[ATTR_ACCESS]→ `scope.attr`

```python
# Find all attribute accesses in the codebase
query_codebase("attribute access self method property", rels="ATTR_ACCESS")

# Find what attributes are accessed on 'con' (database connection)
query_codebase("con execute commit database connection attribute", rels="ATTR_ACCESS", include_symbols=True)

# Explore data flow around the store
pack_snippets("GraphStore edges within attribute access", include_symbols=True)
```

**Current graph:** 945 `ATTR_ACCESS` edges, mostly on `self`, local variables, and module-level objects.

### Scope awareness — what lives in each function

`CodeKGVisitor` tracks `vars_in_scope` per function, seeding all parameter names at function entry. This means semantic queries about parameter patterns are grounded in the correct scope.

```python
# Find functions with specific parameter shapes
pack_snippets("function parameter args kwargs positional keyword-only")

# Find async functions and their argument patterns
pack_snippets("async def fetch url timeout parameter scope")
```

### Default expression scope (a subtle detail)

Default argument values are evaluated in the *enclosing* scope, not the function scope. `CodeKGVisitor` handles this correctly, so queries about default expressions land on the right scope.

```python
# Find module-level constants used as default values
pack_snippets("default value parameter enclosing scope constant")
```

---

## 10. Edge Type Reference

| Edge | Direction | Meaning | Source |
|---|---|---|---|
| `CONTAINS` | module → class, class → method, module → fn | Lexical containment | AST structure |
| `CALLS` | fn/method → fn/method | Direct function call | AST `Call` node |
| `IMPORTS` | module → module | `import` statement | AST `Import`/`ImportFrom` |
| `INHERITS` | class → class | `class Foo(Bar)` | AST `ClassDef.bases` |
| `ATTR_ACCESS` | symbol → symbol | `obj.attr` access | `CodeKGVisitor.visit_Attribute` |
| `READS` *(tracked)* | symbol → — | Variable read | `CodeKGVisitor._extract_reads` |
| `WRITES` *(tracked)* | symbol → — | Variable write | `CodeKGVisitor.visit_Assign` |

> **READS / WRITES** are tracked in `vars_in_scope` per scope but are not yet stored as graph edges (no `target` node is wired). They will become queryable once hooked into edge storage.

---

## 11. Parameter Quick Reference

### `query_codebase` and `pack_snippets` shared params

| Parameter | Default | Effect |
|---|---|---|
| `q` | *(required)* | Natural-language query |
| `k` | `8` | Semantic seed nodes before expansion |
| `hop` | `1` | Graph expansion hops from each seed |
| `rels` | `"CONTAINS,CALLS,IMPORTS,INHERITS"` | Edge types to traverse |
| `include_symbols` | `False` | Include `symbol`-kind nodes (variables, attrs) |
| `max_nodes` | `25` / `15` | Cap returned nodes |

### `pack_snippets` only

| Parameter | Default | Effect |
|---|---|---|
| `context` | `5` | Lines above/below each definition |
| `max_lines` | `60` | Max lines per snippet block |

---

## 12. Common Query Patterns

### "How does X work?"

```python
pack_snippets("X concept or class name")
```

### "What calls Y?"

```python
query_codebase("Y function name", rels="CALLS")
# Then look for edges where dst == Y's node ID
```

### "What does module Z import?"

```python
query_codebase("module Z name", rels="IMPORTS")
```

### "Find all subclasses of Base"

```python
query_codebase("Base class inheritance", rels="INHERITS")
```

### "What attributes does this object touch?"

```python
query_codebase("object variable name attribute", rels="ATTR_ACCESS", include_symbols=True)
```

### "Show me the full structure of this module"

```python
query_codebase("module name", rels="CONTAINS", hop=2)
```

### "Get me the source for function F"

```python
# Step 1: find the node ID
query_codebase("F function description")
# Step 2: fetch it directly
get_node("fn:src/module/path.py:F")
```

---

## 13. This Codebase Live Stats

```
Nodes: 3,093   (class: 17 · function: 209 · method: 80 · module: 21 · symbol: 2,766)
Edges: 2,534   (CALLS: 1,114 · ATTR_ACCESS: 945 · CONTAINS: 306 · IMPORTS: 165 · INHERITS: 4)
DB:    .codekg/graph.sqlite
Model: all-MiniLM-L6-v2
```

*Rebuild after significant code changes: `codekg-build-sqlite --repo . --wipe && codekg-build-lancedb --repo . --wipe`*
