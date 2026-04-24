# Adapter Status Contract

## Background

`KGAdapter.stats()` exists today but returns only `node_count`, `edge_count`, and
`kind` — too thin to be useful at a glance.  This spec upgrades it to a
**standard envelope + domain-specific extension** pattern so that
`kgrag probe` can render a meaningful status table across all 94+ registered KGs.

`analyze()` is not the right tool here: it runs a full structural audit (expensive,
code-specific).  `stats()` should be a fast, live read of what's actually in the DB.

---

## The `stats()` Contract

`KGAdapter.stats()` returns a plain `dict[str, Any]`.  All adapters must populate
the **standard envelope**.  Each adapter then adds **domain-specific keys** that
make sense for its KG kind.  Unknown keys are silently ignored by KGRAG.

### Standard Envelope (required for every adapter)

| key                | type        | description |
|--------------------|-------------|-------------|
| `kind`             | `str`       | KG kind value: `"code"`, `"doc"`, `"meta"`, `"diary"`, etc. |
| `kg_name`          | `str`       | Registered name from `entry.name` |
| `builder_version`  | `str`       | From `entry.builder_version` (read from `_kgrag_meta`) |
| `built_at`         | `str\|None` | ISO-8601 UTC timestamp; read from `_kgrag_meta` at load time |
| `node_count`       | `int`       | Total meaningful nodes (exclude sym: stubs for code) |
| `edge_count`       | `int`       | Total edges |
| `db_size_mb`       | `float`     | SQLite file size in megabytes; `0.0` if unavailable |
| `available`        | `bool`      | `True` if `is_available()` passes |

### Domain-Specific Extensions

Each KG kind extends the envelope with the fields below.  These come from
`self._kg.stats()` in the sister repo — see *Sister Repo Contract* below.

#### `code` (PyCodeKG)

| key                  | type    | source                   |
|----------------------|---------|--------------------------|
| `module_count`       | `int`   | `store.stats()`          |
| `class_count`        | `int`   | `store.stats()`          |
| `function_count`     | `int`   | `store.stats()`          |
| `method_count`       | `int`   | `store.stats()`          |
| `docstring_coverage` | `float` | `store.stats()` (0–1)    |
| `snapshot_count`     | `int`   | snapshot store count     |

#### `doc` (DocKG)

| key               | type  | source           |
|-------------------|-------|------------------|
| `document_count`  | `int` | `store.stats()`  |
| `chunk_count`     | `int` | `store.stats()`  |
| `section_count`   | `int` | `store.stats()`  |
| `topic_count`     | `int` | `store.stats()`  |
| `entity_count`    | `int` | `store.stats()`  |

#### `meta` (MetaboKG)

| key               | type  | source           |
|-------------------|-------|------------------|
| `pathway_count`   | `int` | `store.stats()`  |
| `compound_count`  | `int` | `store.stats()`  |
| `reaction_count`  | `int` | `store.stats()`  |

#### `diary` / `memory` / `verse`

| key               | type        | source           |
|-------------------|-------------|------------------|
| `entry_count`     | `int`       | `store.stats()`  |
| `first_entry_at`  | `str\|None` | `store.stats()`  |
| `last_entry_at`   | `str\|None` | `store.stats()`  |

#### `agent` (AgentKG)

| key           | type  | source           |
|---------------|-------|------------------|
| `turn_count`  | `int` | `store.stats()`  |
| `topic_count` | `int` | `store.stats()`  |
| `session_id`  | `str` | `entry.metadata` |

---

## Sister Repo Contract

Each KG package's main class (e.g. `DocKG`, `PyCodeKG`) must expose a
`stats()` method that returns a flat `dict[str, Any]` containing at minimum
the domain-specific keys listed above, plus whatever extras are natural.

The adapter calls it as `self._kg.stats()` (lazy-loaded after `_load()`).

### Reference implementation — DocKG

```python
# In doc_kg/kg.py (DocKG class)

def stats(self) -> dict[str, Any]:
    """Return live statistics about this DocKG instance.

    :return: Flat dict with counts for documents, chunks, sections,
        topics, and entities.  All values are ints; missing tables
        return 0 rather than raising.
    """
    def _count(table: str) -> int:
        try:
            row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    return {
        "node_count":     _count("nodes"),
        "edge_count":     _count("edges"),
        "document_count": _count("documents"),
        "chunk_count":    _count("chunks"),
        "section_count":  _count("sections"),
        "topic_count":    _count("topics"),
        "entity_count":   _count("entities"),
    }
```

### Reference implementation — PyCodeKG

```python
# In pycode_kg/store.py (GraphStore class — or wherever store.stats() lives)
# This should already return total_nodes, total_edges.
# Add the breakdown:

def stats(self) -> dict[str, Any]:
    def _count(kind: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE kind = ?", (kind,)
        ).fetchone()
        return row[0] if row else 0

    total = _count("module") + _count("cls") + _count("fn") + _count("method")
    with_doc = self._conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE kind IN ('fn','method') AND docstring IS NOT NULL AND docstring != ''"
    ).fetchone()[0]
    fn_method_total = _count("fn") + _count("method")

    return {
        "total_nodes":        ...,   # existing
        "meaningful_nodes":   ...,   # existing
        "total_edges":        ...,   # existing
        "module_count":       _count("module"),
        "class_count":        _count("cls"),
        "function_count":     _count("fn"),
        "method_count":       _count("method"),
        "docstring_coverage": round(with_doc / fn_method_total, 3) if fn_method_total else 0.0,
        "snapshot_count":     ...,   # count rows in snapshots table if present
    }
```

---

## KGRAG Adapter Side

The adapter's `stats()` is responsible for:
1. Calling `_load()` (lazy init)
2. Calling `self._kg.stats()` and forwarding all domain keys
3. **Adding the standard envelope fields** that the KG class doesn't know about:
   `kind`, `kg_name`, `builder_version`, `built_at`, `db_size_mb`, `available`

The `built_at` field should be read once at `_load()` time and cached, so
`stats()` doesn't re-open the DB for meta each call.

```python
# Pattern for every adapter's stats()

def stats(self) -> dict[str, Any]:
    self._load()
    try:
        s = self._kg.stats()
    except Exception:
        s = {}

    db_size = 0.0
    if self.entry.sqlite_path and self.entry.sqlite_path.exists():
        db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)

    return {
        # Standard envelope
        "kind":            self.entry.kind.value,
        "kg_name":         self.entry.name,
        "builder_version": self.entry.builder_version,
        "built_at":        self._built_at,   # cached from _kgrag_meta at _load()
        "node_count":      s.get("meaningful_nodes", s.get("node_count", "n/a")),
        "edge_count":      s.get("total_edges",      s.get("edge_count", "n/a")),
        "db_size_mb":      db_size,
        "available":       self.is_available(),
        # Domain-specific (forwarded from self._kg.stats())
        **{k: v for k, v in s.items() if k not in {
            "total_nodes", "meaningful_nodes", "total_edges",
        }},
    }
```

Cache `built_at` during `_load()`:

```python
def _load(self):
    if self._kg is not None:
        return
    # ... existing load logic ...
    # Cache built_at from _kgrag_meta
    from kg_rag.config import read_kgrag_meta   # new helper, see below
    meta = read_kgrag_meta(self.entry.sqlite_path)
    self._built_at: str | None = meta.get("built_at")
```

Add `read_kgrag_meta(path) -> dict[str, str]` to `kg_rag.config` — reads
all rows from `_kgrag_meta` and returns them as a dict. Already partially
done by `read_builder_version()`; just extend to return all keys.

---

## CLI — `kgrag probe`

```
kgrag probe [NAME]            # single KG by name or ID
kgrag probe --kind doc        # all doc KGs
kgrag probe --corpus NAME     # all KGs in a corpus
kgrag probe                   # all registered KGs (may be slow; warns if > 20)
```

Output is a Rich table:

```
┌────────────────────────────────┬──────┬─────────┬───────┬───────┬──────────┬────────────────────┐
│ Name                           │ Kind │ Builder │ Nodes │ Edges │ DB (MB)  │ Domain Counts      │
├────────────────────────────────┼──────┼─────────┼───────┼───────┼──────────┼────────────────────┤
│ gutenberg-moby-dick-doc        │ doc  │ 0.4.2   │ 3,241 │ 8,102 │ 12.4     │ docs:1 chunks:3241 │
│ code_kg-code                   │ code │ 0.6.1   │ 1,847 │ 5,219 │  8.1     │ fn:812 cov:0.73    │
│ gutenberg-ancient-classical-…  │ doc  │ ?       │ 9,102 │ 22k   │ 34.2     │ docs:9 chunks:9102 │
└────────────────────────────────┴──────┴─────────┴───────┴───────┴──────────┴────────────────────┘
```

The "Domain Counts" column is formatted per kind:
- `doc`: `docs:{n}  chunks:{n}  topics:{n}`
- `code`: `fn:{n}  cov:{pct}%`
- `meta`: `pathways:{n}  compounds:{n}`
- `diary`/`memory`: `entries:{n}  {first}→{last}`
- `agent`: `turns:{n}`

---

## Implementation Checklist

### `kgrag` repo (this repo)

- [ ] Extend `read_builder_version` → `read_kgrag_meta(path) -> dict[str, str]`
      (returns all `_kgrag_meta` keys, not just `builder_version`)
- [ ] Add `_built_at` caching to `_load()` in each adapter
- [ ] Upgrade each adapter's `stats()` to the standard envelope pattern above
- [ ] Add `kgrag probe` CLI command (`src/kg_rag/cli/cmd_probe.py`)
- [ ] Wire `cmd_probe` into the CLI group

### Sister repos (implement `stats()` on the main KG class)

- [ ] **`doc_kg`** — `DocKG.stats()` → add `document_count`, `chunk_count`,
      `section_count`, `topic_count`, `entity_count`
- [ ] **`pycode_kg`** — `GraphStore.stats()` → add `module_count`, `class_count`,
      `function_count`, `method_count`, `docstring_coverage`, `snapshot_count`
- [ ] **`metabokg`** → add `pathway_count`, `compound_count`, `reaction_count`
- [ ] **`diary_kg`** / **`memory_kg`** → add `entry_count`, `first_entry_at`, `last_entry_at`
- [ ] **`agent_kg`** → already has `turn_count`; add `topic_count`

Each sister repo **does not need to know about KGRAG** — `stats()` is just a
method on the KG class. The adapter bridges the two.

---

## Error handling

`stats()` must **never raise**.  Adapters catch all exceptions from
`self._kg.stats()` and return the standard envelope with `n/a` or `0`
for missing fields, plus an `"error": "<message>"` key for debugging.

The probe command shows `[red]error[/red]` in the Domain Counts column
when `"error"` is present in the stats dict.
