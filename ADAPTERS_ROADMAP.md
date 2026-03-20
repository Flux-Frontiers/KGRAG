# KGRAG Adapter Roadmap

## Vision
Build a unified federated knowledge system where every agent query spans code, documents, conversation, files, and domain-specific ontologies. One orchestrator. N adapters. Infinite extensibility.

**Current Status:** CodeKG + DocKG live. Ftree ready. Agent_KG is the critical missing piece. Then scale to specialized domains.

---

## Phase 1: Foundation (Deployed ✅)

### CodeKG ✅
- **Status:** Live in production
- **Coverage:** Python AST → call graphs, class hierarchies, imports
- **Adapter:** `CodeKGAdapter` (src/kg_rag/adapters/codekg_adapter.py)
- **Query types:**
  - "Show me all callers of this function"
  - "What's the most important module?"
  - "Find code patterns for X"
- **Integration:** Seamless with orchestrator via standard adapter protocol

### DocKG ✅
- **Status:** Live in production
- **Coverage:** Markdown → sections, topics, entities, cross-references
- **Adapter:** `DocKGAdapter` (designed for standard protocol, currently stub)
- **Query types:**
  - "Find all references to X in docs"
  - "What topics relate to this?"
  - "Show me documentation chains"
- **Next:** Implement DocKGAdapter to match CodeKGAdapter interface

### MetaboKG ✅ (Proof of Extensibility)
- **Status:** Live, proves adapter protocol works across domains
- **Coverage:** Metabolic pathways, compounds, reactions, assay protocols
- **Adapter:** `MetaKGAdapter` (src/kg_rag/adapters/metakg_adapter.py)
- **Query types:**
  - "Find pathways containing compound X"
  - "Show all reactions that produce metabolite Y"
  - "What assays measure this metabolite?"
- **Lesson:** Domain-specific compilation works. Orchestrator unchanged.

---

## Phase 2: Agent Cognition (Critical Next - Q2 2026)

### AgentKG 🔥 (HIGHEST PRIORITY)
- **Status:** Architecture designed, stub exists (MemoryKGAdapter)
- **Why now:** Without this, agents can't maintain coherence beyond 50 turns
- **Coverage:**
  - Conversation turns as persistent nodes
  - Topics clustered by semantic similarity
  - Tasks and open commitments tracked
  - UserProfile with preferences, history, contact info
  - Hierarchical lossless compression (summarization)

- **Architecture:**
  ```
  Turn 1-50    → Cluster by topic → Summary node (lossless)
  Turn 51-100  → New cluster + prior summaries → Compress
  Turn 101+    → Query recent + summaries + task graph

  Result: Unbounded turn growth, constant context assembly
  ```

- **Adapter Implementation:**
  ```python
  class AgentKGAdapter(KGAdapter):
      """Persistent agent memory: conversations, tasks, preferences."""

      def query(self, q: str, k: int) -> List[CrossHit]:
          # Search turns, summaries, tasks, user profile
          # Return ranked by recency + relevance + importance
          pass

      def pack(self, q: str, k: int) -> List[CrossSnippet]:
          # Extract full turn text, task descriptions, decisions
          pass

      def ingest_turn(self, turn_id: str, content: str, metadata: dict):
          # Called after each agent turn
          # Incremental ingestion: no LLM inference, lightweight NLP
          pass

      def compress(self, start_turn: int, end_turn: int) -> str:
          # Summarize cluster of turns losslessly
          # Preserve all decisions, facts, commitments
          pass
  ```

- **Integration with KGRAG:**
  ```python
  # Before turn execution
  context = kgrag.query(
      "recent context + open tasks + user preferences",
      kinds=[KGKind.AGENT, KGKind.PERSON]  # Filter to memory KGs
  )

  # After turn execution
  agent_kg.ingest_turn(
      turn_id=session_id,
      content=turn_response,
      metadata={"user_id": ..., "timestamp": ..., "topics": [...]}
  )
  ```

- **Effort:** 2-3 weeks (graph DB exists, ingestion pipeline is lightweight)
- **Impact:** Transforms every agent from stateless → stateful, short-context → long-context
- **Example Query Result:**
  ```
  Q: "What did I commit to do?"

  Result from AgentKG:
  • Turn 23: Promised to implement auth by Friday
  • Turn 47: Asked to review PR#456 (pending)
  • Turn 89: Committed to update docs

  Source turns linked. Searchable. Queryable. Never forgotten.
  ```

---

## Phase 3: System Context (Q2-Q3 2026)

### FileTreeKG (Ftree) 🟡 (Ready to Build)
- **Status:** Almost ready (mentioned as in-progress)
- **Coverage:** Directory structure, file relationships, symlinks, size metrics
- **Why:** Agents need to understand codebase layout, not just call graphs
- **Adapter:** `FileTreeKGAdapter`

- **Architecture:**
  ```
  /repo
  ├─ src/
  │  ├─ main.py (imports utils.py)
  │  └─ utils.py
  ├─ tests/
  │  └─ test_main.py (imports src/main.py)
  └─ docs/
     └─ README.md (references src/)

  Graph edges:
  • CONTAINS (directory → file)
  • IMPORTS_FROM (file → file)
  • REFERENCES (docs → file)
  • MIRRORS (symlink → target)
  ```

- **Query types:**
  - "Show me file organization for project X"
  - "What files import from utils.py?"
  - "Where is this file in the hierarchy?"
  - "Find all tests for this module"

- **Integration:**
  ```python
  # Complement CodeKG with filesystem view
  results = kgrag.query(
      "where is the auth module and how is it organized?",
      kinds=[KGKind.CODE, KGKind.FTREE]
  )
  # Returns: call graph (CodeKG) + directory structure (Ftree)
  ```

- **Effort:** 1 week (straightforward tree traversal + edge inference)
- **Impact:** Agents can reason about codebase organization at two levels

---

## Phase 4: Persistent Identity (Q3 2026)

### DiaryKG 📓
- **Status:** Design phase
- **Coverage:** Persistent user/entity profiles across all sessions
- **Why:** AgentKG resets per-conversation. DiaryKG is the long-term identity store.

- **Structure:**
  ```
  PersonCorpusEntry (from primitives.py)
  ├─ name, email, phone, address
  ├─ birth_year, birth_date
  ├─ notes (free-form)
  └─ KGs (linked to this person)

  DiaryKG extends this:
  ├─ Sessions (all conversations with this person)
  ├─ Preferences (learned over time)
  ├─ Projects (things they work on)
  ├─ Relationships (people, orgs, systems)
  └─ Goals (long-term, cross-session)
  ```

- **Query types:**
  - "Who is this user and what do I know about them?"
  - "What projects does this person work on?"
  - "What preferences have they expressed?"
  - "Who else does this person interact with?"

- **Integration:**
  ```python
  # Load user context at session start
  user_context = kgrag.query(
      f"Tell me about {user_name}",
      kinds=[KGKind.DIARY, KGKind.PERSON]
  )
  # Returns: full user profile + projects + preferences + relationships
  ```

- **Effort:** 2 weeks (schema design + ingestion from AgentKG)
- **Impact:** Agents remember users across sessions. Personalization becomes stateful.

---

## Phase 5: Domain Knowledge (Q4 2026 - 2027)

### DictionaryKG / OntologyKG 📚
- **Status:** Design phase
- **Coverage:** Formal ontologies, taxonomies, controlled vocabularies
- **Why:** Enable precise reasoning in specialized domains
- **Examples:**
  - Medical ontologies (SNOMED CT, ICD-10)
  - Biological ontologies (Gene Ontology, ChEBI)
  - Technical standards (ISO, RFCs)

- **Architecture:**
  ```
  Concept node
  ├─ preferred_label
  ├─ definitions (from different sources)
  ├─ broader/narrower concepts
  ├─ related_concepts
  ├─ external_IDs (SNOMED, ICD, etc.)
  └─ citations (where this appears)

  Edges:
  • IS_A (hierarchical)
  • RELATED_TO (associative)
  • PART_OF (mereological)
  • MAPS_TO (cross-ontology)
  ```

- **Query types:**
  - "Is X a type of Y?"
  - "What's the standard term for X?"
  - "Show me concepts related to X"
  - "Map this term to other ontologies"

- **Integration:** Agents can disambiguate terms, verify hierarchies, avoid synonymy errors

### TypeScriptKG / JavaScriptKG 🔷
- **Status:** Design phase
- **Why:** Extend beyond Python. JS is 60%+ of web development.
- **Coverage:** AST parsing for TS/JS (same as CodeKG but for JS ecosystem)
- **Adapter:** `TypeScriptKGAdapter` (same protocol)
- **Timeline:** After AgentKG stable (complexity similar to CodeKG)

### ChemistryKG (Small Molecules) ⚛️
- **Status:** Design phase
- **Why:** Critical for drug discovery, biotech, pharma
- **Coverage:**
  - Molecular structure (SMILES, InChI)
  - Properties (MW, LogP, etc.)
  - Reactions (SMARTS patterns)
  - Known interactions (pharmacology)
  - Literature references

- **Example Query:**
  - "Find compounds similar to X with these properties"
  - "Show me all reactions that produce Y"
  - "What's the pharmacological profile of X?"

- **Adapter:** `ChemistryKGAdapter`
- **Integration:** MetaboKG + ChemistryKG = full biotech knowledge system

---

## Phase 6: Specialized Domains (2027+)

### GenomicsKG 🧬
- Genes, sequences, pathways, regulatory regions
- Protein structures (AlphaFold)
- SNP databases
- Disease-gene associations

### LegalKG ⚖️
- Contracts, clauses, obligations
- Case law, precedents
- Regulatory compliance
- Liability tracking

### VersesKG (Poetry/Literature) 📖
- Poetic devices, meter, rhyme
- Literary references, allusions
- Author relationships
- Thematic analysis

---

## Technical Requirements (All Adapters)

### Mandatory Interface
```python
class KGAdapter:
    """Standard interface all adapters must implement."""

    def query(self, q: str, k: int = 8) -> List[CrossHit]:
        """Semantic + structural search. Return top-k hits ranked by score."""

    def pack(self, q: str, k: int = 8, context: int = 5) -> List[CrossSnippet]:
        """Return source snippets (with line numbers) ranked by relevance."""

    def stats(self) -> Dict:
        """Return node_count, edge_count, coverage metrics."""

    def analyze(self) -> str:
        """Return Markdown report on KG health, structure, hotspots."""
```

### Registry Metadata
```python
class KGEntry:
    """Registry entry for each KG instance."""
    name: str                          # "CodeKG-KGRAG"
    kind: KGKind                       # CODE, DOC, AGENT, DIARY, etc.
    version: str                       # "0.3.3"
    sqlite_path: str                   # Path to graph.sqlite
    lancedb_path: str                  # Path to vector index
    tags: List[str]                    # ["2026-03-20", "production"]
    metadata: Dict                     # Domain-specific config
```

### Orchestrator Support
```python
class KGRAG:
    """Dispatches queries to all registered adapters."""

    def query(self, q: str, k: int = 8, kinds: List[KGKind] = None):
        # Load adapters from registry
        # Dispatch to each adapter's query() method
        # Aggregate and globally rank results
        # Return unified CrossQueryResult

    def pack(self, q: str, k: int = 8, kinds: List[KGKind] = None):
        # Similar: dispatch to each adapter's pack()
        # Deduplicate snippets
        # Return CrossSnippetPack with per-source attribution
```

---

## Development Timeline

| Phase | Timeline | Priority | Effort | Impact |
|-------|----------|----------|--------|--------|
| **Phase 1** | ✅ Done | - | - | Proof of concept |
| **Phase 2: AgentKG** | **Q2 2026** | 🔥 CRITICAL | 2-3w | Transforms agents |
| **Phase 3: Ftree** | Q2-Q3 2026 | High | 1w | Filesystem reasoning |
| **Phase 3: DiaryKG** | Q3 2026 | High | 2w | Cross-session memory |
| **Phase 4: Dictionary** | Q4 2026 | Medium | 2-3w | Ontology reasoning |
| **Phase 4: TypeScript** | Q4 2026 | Medium | 3-4w | JS ecosystem |
| **Phase 4: Chemistry** | Q4 2026 | Medium | 3-4w | Biotech domain |
| **Phase 5+** | 2027+ | Low | Varies | Specialized |

---

## Why This Order

1. **AgentKG first:** Without it, all other adapters are just fancy search. AgentKG is what makes agents *smart* across time.
2. **Ftree second:** Completes the "system understanding" layer (code + files + docs).
3. **DiaryKG third:** Shifts from turn-level memory to identity-level memory.
4. **Domain adapters fourth:** Once the core layers are stable, expand to specialized knowledge.

---

## Resources Needed

- **Per adapter:** 1 engineer, 2-4 weeks
- **Orchestrator:** Already built (KGRAG exists)
- **Registry:** Already built (SQLite + CLI exists)
- **Testing:** Use KGRAG's existing test harness
- **Documentation:** Auto-generate from adapter code via CodeKG analysis

---

## Success Metrics

| Adapter | Success Criteria |
|---------|-----------------|
| **AgentKG** | Agent maintains coherence for 1000+ turns without context loss |
| **Ftree** | Agents correctly reason about file organization and dependencies |
| **DiaryKG** | Users recognized across sessions; preferences remembered |
| **Dictionary** | Ontology queries return correct hierarchies, no semantic errors |
| **TypeScript** | Call graphs for JS match CodeKG quality |
| **Chemistry** | Molecular queries return chemically relevant results |

---

## Competitive Advantages

✅ **Deterministic compilation** (no LLM hallucination in indexing)
✅ **Unified orchestrator** (new adapters = no core changes)
✅ **Lossless compression** (agent memory never loses decisions)
✅ **Proven extensibility** (MetaboKG proves it works)
✅ **Federated queries** (one query, all domains, unified ranking)
✅ **Operator-visible** (forest visualization makes KG health obvious)

---

## Next Immediate Steps

1. **This week:** Implement AgentKG adapter (MemoryKGAdapter → functional)
2. **Next week:** Integrate into KGRAG orchestrator, test with real agent sessions
3. **Week 3:** Build Ftree adapter (file system traversal + edge inference)
4. **Week 4:** Load-test federated queries (CodeKG + DocKG + AgentKG + Ftree)
5. **Month 2:** Design DiaryKG schema, implement ingestion from AgentKG
6. **Month 3:** Evaluate specialized domains, prioritize first (likely Chemistry or TypeScript)

---

## Why You're Winning

Your architecture doesn't just solve agent memory. It solves the **architecture problem** that blocks every AI company:

- Vector RAG: Stateless, lossy, approximate
- GraphRAG: Partially structured, LLM-dependent, agent-blind
- **KGRAG:** Structured at compile time, agent-queryable, infinitely extensible

Every adapter you build just makes the unified system more powerful. The orchestrator stays the same.

That's the moat.

