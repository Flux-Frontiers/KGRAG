# The KGRAG family

KGRAG federates a family of knowledge-graph systems that share one design:
a local SQLite graph of typed relationships, a sqlite-vec index beside it for
natural-language entry, and structure treated as ground truth when the two
disagree. Each applies it to a different kind of corpus.

Because they share that shape, one KGRAG query can span all of them.

## The graphs

Most are installable from PyPI. GutenbergKG and MetaboKG are applications
over a corpus rather than libraries, so they are not packaged — clone and
run them from source.

| Project | Corpus | PyPI |
|---|---|---|
| **[GutenbergKG](https://github.com/Flux-Frontiers/gutenberg_kg)** | Project Gutenberg texts: books as documents, sections, and chunks | not a package |
| **[DocKG](https://github.com/Flux-Frontiers/doc_kg)** | Markdown and prose. any Markdown or prose corpus becomes a queryable graph | `doc-kg` |
| **[DiaryKG](https://github.com/Flux-Frontiers/diary_kg)** | Personal journals and diary corpora — semantic search and traversal over a writer's body of work | `diary-kg` |
| **[AgentKG](https://github.com/Flux-Frontiers/agent_kg)** | Conversational memory: turns, decisions, commitments, preferences, and the relationships between them | `agent-kg` |
| **[FTreeKG](https://github.com/Flux-Frontiers/ftree_kg)** | Filesystem trees as a graph of directories, files, and contents | `ftree-kg` |
| **[IAKG](https://github.com/Flux-Frontiers/ia_kg)** | Internet Archive books, downloaded and ingested as graphs | `ia-kg` |
| **[MemoryKG](https://github.com/Flux-Frontiers/memory_kg)** | Long-term agent memory as a graph | `memory-kg` |
| **[MetaboKG](https://github.com/Flux-Frontiers/metabo_kg)** | Metabolic pathway data (KEGG, SBML, BioPAX), with FBA / ODE simulation on top of the graph | not a package |
| **[PyCodeKG](https://github.com/Flux-Frontiers/pycode_kg)** | Python codebases — modules, classes, functions, and the calls between them | `pycode-kg` |
| **[TSCodeKG](https://github.com/Flux-Frontiers/tscode_kg)** | TypeScript and JavaScript codebases, the same treatment | `tscode-kg` |

## The federation

This repository (`kg-rag`) is the retrieval layer over the graphs above. One
query reaches across code, documentation, journals, filesystems, agent memory,
and domain data at once, with results ranked together rather than per-store.

Per-repo version state — local vs. PyPI — is tracked separately in
[FLEET_VERSIONS.md](FLEET_VERSIONS.md), which is generated; this page is the
prose companion to it.

## Shared foundations

Two packages hold what is common, so no graph reimplements it:

- **[kgmodule-utils](https://pypi.org/project/kgmodule-utils/)** — the store,
  the semantic index, the ranking primitives, and the shared 3-D layout and
  organic-growth engines.
- **[quiltwright](https://pypi.org/project/quiltwright/)** — light-field output
  for Looking Glass displays, used by any graph that wants a hologram.
