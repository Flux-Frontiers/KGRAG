# KG Builder Version Stamp — Contract

Each KG builder package (`doc_kg`, `pycode_kg`, `metabokg`, `memorykg`,
`diarykg`, …) is expected to **stamp its own version** into the built
SQLite database at build time. KGRAG reads this stamp when registering the
KG and surfaces it through `kgrag info`, `kgrag corpus info`, and
`kgrag person info`.

This is the schema/ingestion contract, not the source-repo version.
For a doc corpus assembled from a loose collection of files, the repo
version (`KGEntry.version`) is meaningless — the builder version
(`KGEntry.builder_version`) is the one that matters.

---

## Contract

Inside the built SQLite file, after all other tables are created, write
the following:

```sql
CREATE TABLE IF NOT EXISTS _kgrag_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR REPLACE INTO _kgrag_meta (key, value) VALUES ('builder_name',    ?);
INSERT OR REPLACE INTO _kgrag_meta (key, value) VALUES ('builder_version', ?);
INSERT OR REPLACE INTO _kgrag_meta (key, value) VALUES ('built_at',        ?);
```

Required keys:

| key               | meaning                                         |
|-------------------|-------------------------------------------------|
| `builder_name`    | Package name (e.g. `"doc_kg"`)                  |
| `builder_version` | `__version__` of the builder package            |
| `built_at`        | ISO-8601 UTC timestamp (`datetime.now(UTC).isoformat()`) |

Additional keys are allowed (e.g. `schema_version`, `commit_sha`) — KGRAG
ignores unrecognized keys.

---

## Minimal reference implementation

Drop this helper into your build pipeline (e.g. at the end of
`doc_kg build`, right before closing the connection):

```python
import sqlite3
from datetime import UTC, datetime

def stamp_kgrag_meta(
    conn: sqlite3.Connection,
    *,
    builder_name: str,
    builder_version: str,
) -> None:
    """Stamp the KGRAG builder-version metadata into a built KG SQLite.

    :param conn: Open SQLite connection to the built KG file.
    :param builder_name: Builder package name (e.g. ``"doc_kg"``).
    :param builder_version: Builder package ``__version__``.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _kgrag_meta "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    built_at = datetime.now(UTC).isoformat()
    conn.executemany(
        "INSERT OR REPLACE INTO _kgrag_meta (key, value) VALUES (?, ?)",
        [
            ("builder_name", builder_name),
            ("builder_version", builder_version),
            ("built_at", built_at),
        ],
    )
    conn.commit()
```

Then, at the end of the build command:

```python
from doc_kg import __version__ as DOC_KG_VERSION

stamp_kgrag_meta(
    conn,
    builder_name="doc_kg",
    builder_version=DOC_KG_VERSION,
)
```

---

## Verification

After rebuilding a KG, verify the stamp landed:

```bash
sqlite3 .dockg/graph.sqlite "SELECT * FROM _kgrag_meta;"
```

Expected output:

```
builder_name|doc_kg
builder_version|0.4.2
built_at|2026-04-23T22:04:11.912341+00:00
```

Then re-register (or use `kgrag scan --auto-register`) and `kgrag info`
should show:

```
Builder  : 0.4.2
```

---

## Back-compat

- Pre-stamp databases read as `builder_version = "unknown"`. No error.
- KGRAG's `read_builder_version()` gracefully returns `"unknown"` when
  the `_kgrag_meta` table is absent, the DB file is missing, or the file
  is corrupt.
- The `_kgrag_meta` prefix is reserved. Do not use it for your own
  domain tables.
