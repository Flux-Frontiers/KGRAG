# KGRAG Vision: The Knowledge Compiler for All Domains

## The Central Insight: Ontology Enables Determinism

The power of knowledge-graph retrieval scales directly with how well-defined the
ontology of the source domain is.

A **well-defined ontology** is one where the entities, their relationships, and
the rules governing those relationships are formally specified — not inferred, not
approximated, but written down and enforced by construction. When you have that,
you can build a knowledge graph that is *correct by construction*: every node
corresponds to a real thing in the source; every edge corresponds to a verified
relationship.

The best example on the planet is a **programming language**. Python's grammar is
a precise formal specification. Every function, class, import, and call site in
every `.py` file can be extracted deterministically from the abstract syntax tree.
The call graph is not an approximation — it is a theorem about the source code.
CodeKG exploits this fully: 2,682 nodes, 3,752 edges, all derived from syntax
with no language model involvement.

But programming languages are not unique. The same principle holds across a
surprising breadth of domains:

| Domain | Formal structure | KG kind |
|--------|-----------------|---------|
| Python source code | Abstract syntax tree | `code` |
| Markdown / RST documentation | Document parse tree, cross-references | `doc` |
| Biochemical pathways | Reaction schemas (KEGG, BioCyc) | `meta` |
| Protein structures | PDB file format (ATOM, SEQRES records) | `pdbfile` |
| Disulfide bond networks | Bond topology derived from PDB coordinates | `disulfide` |
| Books of law | Hierarchical statute structure (Title → Chapter → Section → Clause) | `legal` |
| Diary entries | Document structure + temporal ordering | `diary` |
| Scripture / verse | Book → Chapter → Verse hierarchy, cross-references | `verse` |
| Episodic memory | Temporal event graphs | `memory` |
| Personal knowledge | Biographical and relational graphs | `person` |

In every case: the formal structure of the source *is* the ontology.
A knowledge graph derived from it carries the same guarantees as the source itself.

---

## KGRAG as a Knowledge Compiler

A **compiler** transforms source code into a lower-level representation that
preserves the meaning of the original but makes it more useful for a different
purpose — execution, optimization, analysis. It does not guess what the programmer
meant. It reads the formal language and produces a deterministic output.

KGRAG is a knowledge compiler:

1. **Source** — formally structured artifacts: Python files, Markdown corpora,
   PDB files, statutes, diary entries, scripture
2. **Compilation** — deterministic parsers extract nodes and edges based on the
   grammar and ontology of each domain
3. **Output** — a structural knowledge graph stored in SQLite + a semantic index
   in LanceDB, together forming a queryable, traversable representation of the source

The compiled knowledge graph is not a *summary* of the source. It is a
*relational representation* of the source — compressed for navigation, expanded
for retrieval. Just as compiled machine code is the source, the knowledge graph
*is* the corpus, represented as a graph.

This framing has a crucial implication: **the knowledge graph cannot be wrong in
ways the source is not wrong.** If a function call is in the AST, the edge is in
the graph. If a statute cross-references another section, the edge is in the graph.
There is no extraction step where errors can be silently introduced.

---

## Federated Search: One Interface for All Knowledge

The compilation metaphor scales. Once every domain compiles to the same interface
(`KGAdapter`: `query`, `pack`, `stats`, `analyze`), the federation layer treats
them all identically:

```
kgrag query "disulfide bond formation mechanism"
```

This single query fans out to every registered KG — code, documentation,
pathway data, PDB files, legal corpus, diary entries, whatever is registered —
ranks all results globally by relevance, and returns a unified list with full
provenance. The user or agent does not need to know which backend answered or how.

This is the **ultimate power of the design**: not that any individual KG is
especially capable, but that **all domains are queryable through a single
coherent interface**. The scientist studying disulfide bonds can query their
Python analysis code, the PDB corpus, the pathway database, and the relevant
literature simultaneously, with one command, and get globally ranked results.

---

## Grounded Synthesis: The End of Hallucination

When KGRAG output is passed to a large language model for synthesis, something
important happens: the model is given *facts*, not asked to *construct* facts.

Every item in a KGRAG result carries:
- A stable node identifier encoding its origin (e.g. `fn:src/auth.py:JWTValidator.validate`)
- A source path and line span
- A relevance score computed deterministically
- The actual source text, not a summary

The language model's job is **synthesis** — reasoning over the provided context,
connecting ideas, formulating an explanation. It is not asked to remember facts
it may have seen in training, hallucinate plausible-sounding details, or bridge
gaps with guesses.

When the context is structurally grounded:
- Every claim can be traced to a source address
- The model cannot introduce facts that are not in the context
- Every statement in the synthesis is either directly supported by a KGRAG node
  or is a logical inference over supported nodes

This combination — **deterministic knowledge compilation + language model
synthesis** — eliminates the hallucination risk at the knowledge layer entirely.
The remaining risk (reasoning errors in synthesis) is what language models are
actually good at defending against with chain-of-thought, verification, and
re-querying. There is no risk of hallucination in the *facts* — only in the
*reasoning*, which the LLM is equipped to handle.

---

## Corpus and Person Abstractions

Knowledge about real things does not live in one KG. A research project has code,
documentation, data files, and notes. A person has diaries, memories,
correspondence, and a body of work. A legal question spans statutes, regulations,
case law, and commentary.

KGRAG addresses this with two grouping abstractions:

**Generic Corpus** — a named collection of KG instances that can be queried as a
unit. A `law-library` corpus might contain `us-code`, `cfr`, `supremecourt`, and
`law-review`. One query across all of them:

```bash
kgrag corpus create law-library \
    --kg us-code --kg cfr --kg supremecourt --kg law-review
kgrag corpus query law-library "first amendment balancing tests"
```

**Person Corpus** — a corpus enriched with personal metadata (birth year, address,
email, notes) grouping all KGs relevant to an individual: diary, memory, verse,
code, documents. A natural container for building a rich personal knowledge base:

```bash
kgrag corpus person create "Eric Suchanek" \
    --kg eric-diary --kg eric-memories --kg disulfide-research \
    --birth-year 1962 --email eric@flux-frontiers.com
kgrag corpus person query "Eric Suchanek" "disulfide research 2019"
```

These abstractions make the system not merely multi-domain but **multi-context**:
you can scope queries to exactly the corpus of knowledge relevant to a given
question.

---

## TreeOfKnowledge(tm): The Corpus Scientia

The logical endpoint of this design is **TreeOfKnowledge(tm)** — the *Corpus
Scientia*:

> **All human knowledge. All domains. One interface. One query.**

Every domain where a formal ontology exists — and that is most of the domains
worth knowing about — can be compiled into a KG and registered. Every registered
KG participates in federated query. The result is a single interface that spans:

- **All source code** — structured as ASTs, call graphs, module dependency trees
- **All scientific literature** — structured as citation graphs, pathway ontologies, protein topologies
- **All legal codes** — structured as statutory hierarchies, regulatory cross-references, case precedent chains
- **All biological structure** — structured as PDB files, reaction schemas, bond networks
- **All personal knowledge** — structured as diary timelines, memory graphs, correspondence networks
- **All cultural knowledge** — structured as scripture hierarchies, verse annotations, commentary threads

Coupled with the largest language model and context window available, this is
not retrieval-augmented generation — it is **knowledge-compiler-augmented
synthesis**. The model receives the relevant subgraph of all human knowledge,
structured and provenance-tagged, and synthesizes an answer that can be traced
to its sources.

This is not science fiction. KGRAG implements the federation layer today. The
remaining work is building the domain-specific compilers (KG backends) for each
new kind. The architecture is designed exactly for this: each new domain requires
implementing five adapter methods. The orchestrator, registry, CLI, MCP server,
and corpus abstractions require no changes.

**The framework is the answer. The domains are the data.
The TreeOfKnowledge is the union.**

---

## Design Philosophy

### Structure over Approximation
Formal structure is authoritative. Semantic embeddings accelerate entry; graph
traversal decides what is returned. The structural layer is never bypassed.

### Provenance at Every Node
Every result is traceable to a source address. Nothing enters a result without
a node ID, file path, and line span. The synthesis model receives facts, not
embeddings.

### One Protocol, Any Domain
The `KGAdapter` interface is the universal boundary. Five methods expose any
domain to the federation layer. New domains extend the system without modifying it.

### Graceful Incompleteness
Domains whose backing libraries are not yet built are registered as stubs. They
participate in the registry, report their kind and metadata, and return empty
results until their compiler is ready. The system is always complete in structure;
progressively complete in data.

---

## Current Status

| Layer | Status |
|-------|--------|
| Federation orchestrator (`KGRAG`) | Complete |
| Registry (`KGRegistry`) | Complete |
| Corpus registry (`CorpusRegistry`) | Complete |
| Person corpus registry (`PersonCorpusRegistry`) | Complete |
| CLI (all commands + corpus/person subcommands) | Complete |
| MCP server (registry + corpus + person tools) | Complete |
| CodeKG adapter | **Available** |
| DocKG adapter | **Available** |
| MetaKG adapter | **Available** |
| DiaryKG, VerseKG, MemoryKG adapters | Stubbed — libraries pending |
| DisulfideKG, PDBFileKG adapters | Stubbed — libraries pending |
| LegalKG adapter | Stubbed — library pending |
| PersonKG adapter | Stubbed — library pending |

---

## See Also

- [USAGE.md](USAGE.md) — Commands, workflows, examples
- [INSTALLATION.md](INSTALLATION.md) — Setup and configuration
- [MCP.md](MCP.md) — MCP server configuration and tools
- [ADAPTER_SPEC.md](ADAPTER_SPEC.md) — How to implement a new KG adapter
