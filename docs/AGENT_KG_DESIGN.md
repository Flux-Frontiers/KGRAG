# AgentKG Design: Conversational Memory as a Knowledge Graph

**Status:** Proposal
**Author:** egs + Claude Sonnet 4.6
**Date:** 2026-03-19

---

## The Problem: Context Rot

LLMs operate within a fixed context window. As a conversation grows, two failure modes emerge:

1. **Truncation rot** — the model silently drops the oldest content. Early decisions, constraints, and established facts disappear without warning.
2. **Diffusion rot** — even before truncation, a long flat context dilutes relevance. The model must attend equally to everything, so early material receives proportionally less weight.

Current mitigations (summaries, RAG retrieval, memory files) treat symptoms, not causes. They are lossy, static, or require explicit user management.

**The root insight:** conversation is not a list of messages — it is a *graph* of topics, intents, entities, tasks, and their relationships through time. Representing it as a flat string wastes the structure.

---

## The Solution: AgentKG

AgentKG is a live, in-session knowledge graph that represents the full conversational state. It is:

- **Incremental** — updated on every turn, not at conversation end
- **Queryable** — the agent retrieves relevant context semantically, not by position
- **Prunable** — when the graph grows large, a compression pass (KG Context Pruning) rebuilds a smaller, semantically coherent graph
- **Transparent** — the graph is inspectable; the agent can explain what it knows and why
- **Person-aware** — connected to the KGRAG `PersonCorpus` for the user, federating conversation memory with diary, long-term memory, and project knowledge

AgentKG is implemented as a new KG kind (`KGKind.AGENT`) in the KGRAG adapter framework, following the same contract as `DiaryKGAdapter`.

AgentKG contains **two structurally distinct persistent trees** with different lifecycle semantics:

| Tree | Contents | Lifecycle |
|------|----------|-----------|
| **Conversation tree** | `Turn`, `Topic`, `Intent`, `Entity`, `Task`, `Summary` | Grows each session; old nodes pruned into `Summary` nodes |
| **UserProfile tree** | `Preference`, `Style`, `Interest`, `Expertise`, `Commitment` | Never pruned; only updated. Persists across all sessions and projects |

The UserProfile tree is populated by the **Agent Onboarding Skill** at first run and enriched incrementally as the agent learns more about the user through interaction.

---

## Graph Schema

### Node Types

| Kind | Description | Key Fields |
|------|-------------|------------|
| `Turn` | One user or agent message | `role`, `text`, `timestamp`, `turn_index`, `token_count` |
| `Topic` | A subject being discussed | `label`, `canonical_form`, `first_seen`, `last_seen` |
| `Intent` | What the user is trying to accomplish | `label`, `category` (question/request/correction/confirmation) |
| `Entity` | A named thing mentioned | `label`, `kind` (file/function/concept/person/project), `source` |
| `Task` | A concrete action requested or completed | `description`, `status` (open/in_progress/completed/abandoned) |
| `Summary` | A compression of a pruned subgraph | `text`, `covers_turns`, `created_at`, `pruning_pass` |

### Edge Types

| Relation | From → To | Meaning |
|----------|-----------|---------|
| `FOLLOWS` | Turn → Turn | Temporal sequence |
| `ADDRESSES` | Turn → Topic | This turn discusses this topic |
| `EXPRESSES` | Turn → Intent | This turn carries this intent |
| `MENTIONS` | Turn → Entity | This entity appears in this turn |
| `CREATES` | Turn → Task | This turn initiates a task |
| `RESOLVES` | Turn → Task | This turn completes or closes a task |
| `RELATED_TO` | Topic ↔ Topic | Semantic proximity between topics |
| `REFERENCES` | Turn → Entity/Topic | Explicit reference to prior context |
| `COMPRESSED_INTO` | Turn → Summary | This turn was folded into a summary node |
| `EXPANDS` | Summary → Topic/Entity | Summary covers these concepts |

### Properties Common to All Nodes
- `embedding: list[float]` — sentence-transformer vector
- `created_at: datetime`
- `pruning_pass: int` — 0 = original, N = survived N pruning passes

---

## UserProfile Tree

The UserProfile tree is a **globally persistent subgraph stored in user space** (`~/.kgrag/profiles/<person_id>/`), co-located with the KGRAG registry and `PersonCorpusEntry`. It is explicitly *not* repo-scoped — preferences, expertise, and personal interests belong to the person, not the project.

Storing it in user space means:
- One canonical UserProfile across all repos and sessions — no drift, no N copies
- `kgrag person info "Eric"` is always current regardless of which repo you're in
- The profile survives repo deletion, `--wipe`, or any `.agentkg/` operation

It is never subject to KG Context Pruning — it only grows and is updated in place.

### Node Types

| Kind | Description | Examples |
|------|-------------|---------|
| `Preference` | An expressed preference with a category | `code_style: "prefer type annotations"`, `verbosity: "concise"` |
| `Style` | A coding or communication style trait | `"docstrings: Google style"`, `"no trailing summaries"` |
| `Interest` | A personal interest or hobby | `"sailing"`, `"computational biology"`, `"jazz"` |
| `Expertise` | A domain of deep knowledge | `"Python"`, `"metabolic pathway modeling"`, `"knowledge graphs"` |
| `Commitment` | A standing instruction or rule | `"always run ruff before committing"`, `"never use --no-verify without asking"` |
| `Context` | Stable background facts | `"primary machine: Turing (macOS)"`, `"works across repos/kgrag, repos/code_kg"` |

### Edge Types

| Relation | Meaning |
|----------|---------|
| `PREFERS` | UserProfile → Preference/Style |
| `INTERESTED_IN` | UserProfile → Interest |
| `EXPERT_IN` | UserProfile → Expertise |
| `COMMITTED_TO` | UserProfile → Commitment |
| `UPDATED_BY` | Turn → Preference (when a conversation turn refines a preference) |
| `CONFLICTS_WITH` | Preference ↔ Preference (detected contradictions flagged for resolution) |

### Lifecycle

- **Created**: Agent Onboarding Skill at first session, or first `kgrag person create` for this user
- **Updated**: Any turn where the user expresses a preference, corrects the agent, or provides personal context triggers a `UPDATED_BY` edge and updates the node's value + `updated_at`
- **Never pruned**: UserProfile nodes survive all pruning passes; `pruning_pass` is always `None`
- **Synced to PersonCorpusEntry**: key fields (`expertise`, `interests`, `commitments`) are mirrored into `PersonCorpusEntry.metadata` so they are visible to all KGRAG tools, not just AgentKG

### Agent Onboarding Skill

A dedicated `/onboard` skill (or runs automatically on first session) conducts a structured interview:

```
Phase 1 — Identity & Context
  "What's your name and primary role?"
  "What projects are you mainly working in?"
  "What machine/OS are you on?"

Phase 2 — Coding Style
  "Preferred language(s) and style conventions?"
  "Docstring format? (Google / NumPy / Sphinx / none)"
  "How verbose do you want my responses? (concise / detailed / adaptive)"
  "Any standing rules I should always follow?"

Phase 3 — Domain Expertise
  "What are your strongest technical domains?"
  "What are you currently learning or exploring?"

Phase 4 — Personal (optional, skip-able)
  "Any hobbies or interests you'd like me to know about?"
  "Anything that helps us work better together?"
```

Each answer is parsed by the NLP pipeline and stored as typed `Preference`, `Expertise`, `Interest`, or `Commitment` nodes. The skill is re-runnable (`/onboard --update`) to refine preferences at any time.

The agent also learns *implicitly*: when the user says "stop doing X" or "always do Y", a `Commitment` node is created or updated without requiring an explicit onboarding run.

---

---

## Two-Phase Build

Unlike CodeKG (build-on-commit) or DocKG (build-on-file-scan), AgentKG is built *live* during a session.

### Phase 1 — Instantaneous (per turn, synchronous)

Triggered on every incoming user message:

1. **Sentence parse**: split turn into sentences; run lightweight NLP (spaCy or equivalent) to extract:
   - Named entities → `Entity` nodes
   - Noun chunks + verb phrases → candidate `Topic` nodes
   - Interrogative / imperative detection → `Intent` category

2. **Deduplication**: fuzzy-match extracted topics/entities against existing nodes; merge if cosine similarity > threshold (0.88)

3. **Graph update**:
   - Create `Turn` node
   - Add `FOLLOWS` edge from previous turn
   - Add `ADDRESSES`, `EXPRESSES`, `MENTIONS` edges
   - Create or merge `Topic`, `Intent`, `Entity` nodes
   - Update `last_seen` timestamps

4. **Embed**: compute sentence-transformer embedding for the turn text and any new nodes (async, non-blocking)

Result: the graph is always current, even mid-conversation. This is the **incremental layer**.

### Phase 2 — Background Consolidation (periodic or on-demand)

Triggered when turn count exceeds a threshold (default: 20 turns) or explicitly via `agent_kg consolidate`:

- Run full embedding pass over any nodes with stale or missing vectors
- Re-compute `RELATED_TO` edges between `Topic` nodes using cosine similarity
- Update `Task` statuses by re-reading `RESOLVES` edges

---

## KG Context Pruning

This is the core innovation. When the graph grows too large for efficient retrieval, pruning compresses old subgraphs into dense `Summary` nodes while preserving semantic coherence.

### Algorithm

```
def prune(graph, model, token_budget):
    # 1. Identify cold subgraph
    cold_turns = [t for t in graph.turns if t.turn_index < graph.current - WINDOW]
    cold_component = graph.subgraph(cold_turns + their_topic_entity_nodes)

    # 2. Cluster by topic proximity
    clusters = topic_cluster(cold_component, min_cluster_size=3)

    for cluster in clusters:
        # 3. Extract cluster text
        texts = [t.text for t in cluster.turns]
        context = "\n".join(texts)

        # 4. Summarize via LLM
        summary_text = llm.summarize(
            f"Summarize this conversation segment preserving all facts, "
            f"decisions, and open questions:\n\n{context}"
        )

        # 5. Create Summary node
        summary_node = Summary(
            text=summary_text,
            covers_turns=[t.id for t in cluster.turns],
            pruning_pass=graph.pruning_pass + 1,
            embedding=embed(summary_text),
        )

        # 6. Rewire edges
        for entity in cluster.entities:
            graph.add_edge(summary_node, entity, rel="EXPANDS")
        for topic in cluster.topics:
            graph.add_edge(summary_node, topic, rel="EXPANDS")

        # 7. Remove original nodes
        graph.remove(cluster.turns)

    graph.pruning_pass += 1
    return graph
```

### Properties of Pruned Graphs

- **Lossless semantics** — the summary captures all decisions, facts, and open questions; not just a topic label
- **Traversable** — `EXPANDS` edges allow reconstruction of what topics/entities a summary covers
- **Composable** — summaries can themselves be pruned in a second pass (hierarchical compression)
- **Comparable** — embedding distance between `Summary` nodes reveals topic drift across the conversation

### Pruning Triggers

| Trigger | Condition |
|---------|-----------|
| Turn count | `len(cold_turns) > 30` |
| Token budget | Graph token equivalent exceeds 60% of context window |
| Explicit | `agent_kg prune --budget 2000` |
| Pre-retrieval | Before packing context for downstream model |

---

## Context Assembly: Defeating Context Rot

When the agent needs to answer a new question, instead of dumping the raw context window, it assembles context from the graph:

```
def assemble_context(graph, current_query, token_budget):
    # 1. Semantic retrieval: find relevant nodes
    relevant = graph.query(current_query, k=8)

    # 2. Walk temporal spine: include recent verbatim turns
    recent = graph.turns[-RECENT_WINDOW:]

    # 3. Include open tasks
    open_tasks = [t for t in graph.tasks if t.status == "open"]

    # 4. Pack into token budget
    context = pack(
        summaries=relevant.summaries,    # compressed old context
        recent_turns=recent,             # verbatim recent context
        open_tasks=open_tasks,           # active commitments
        budget=token_budget,
    )
    return context
```

This produces context that is:
- **Semantically relevant** — not positionally biased
- **Token-bounded** — respects the downstream model's window
- **Temporally aware** — recent turns are always verbatim; old context is summarized
- **Commitment-preserving** — open tasks never drop out

---

## KGRAG Integration

### New KG Kind

```python
class KGKind(str, Enum):
    # ... existing kinds ...
    AGENT = "agent"  # conversational agent memory
```

### AgentKGAdapter

Follows `DiaryKGAdapter` as the reference implementation:

```python
class AgentKGAdapter(KGAdapter):
    """Adapter wrapping AgentKG — live conversational memory graph.

    Unlike static KGs, AgentKG is mutated during a session.
    The adapter exposes both query/pack (read) and ingest/prune (write)
    operations, making it unique among KGAdapters.
    """

    _kind = KGKind.AGENT

    def ingest(self, turn: Turn) -> None:
        """Phase 1 incremental update — call on every conversation turn."""

    def prune(self, token_budget: int | None = None) -> PruneReport:
        """KG Context Pruning — compress old subgraphs into Summary nodes."""

    def assemble_context(self, query: str, budget: int) -> str:
        """Return assembled Markdown context for a downstream model."""

    # Standard KGAdapter contract
    def query(self, q: str, k: int = 8) -> list[CrossHit]: ...
    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]: ...
    def stats(self) -> dict[str, Any]: ...
    def analyze(self) -> str: ...
```

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `agent_kg_ingest(turn_text, role)` | Add a turn to the graph (Phase 1) |
| `agent_kg_query(q, k)` | Semantic search over the conversation graph |
| `agent_kg_pack(q, budget)` | Assemble context for downstream model |
| `agent_kg_prune(budget)` | Trigger KG Context Pruning |
| `agent_kg_tasks()` | List all open tasks extracted from conversation |
| `agent_kg_stats()` | Node/edge counts, pruning pass, topic distribution |
| `agent_kg_topics()` | List all topics with recency and salience scores |

---

## Backing Library: `agent_kg`

New KGModule package scaffolded via `/new-kg-module agent_kg`. See **Revised Package Layout** in the Resolved Design Decisions section for the full directory tree.

Storage: SQLite for graph topology (nodes, edges, properties) + LanceDB for embeddings — identical to the two-layer architecture used by CodeKG and DocKG. Session index in `sessions.jsonl`. Snapshot format mirrors `code_kg.snapshots` / `doc_kg.snapshots`.

---

## Why This Actually Solves Context Rot

| Problem | Standard approach | AgentKG approach |
|---------|-------------------|-----------------|
| Truncation | Drop oldest tokens | Prune oldest turns into Summary nodes; nothing lost |
| Diffusion | Flat attention over all context | Query retrieves only relevant nodes; recency bias preserved |
| Open tasks lost | Rely on user to restate | `Task` nodes with status; always included in context assembly |
| Topic drift invisible | None | `RELATED_TO` edges + topic timeline show drift explicitly |
| No self-awareness | Model doesn't know what it knows | `agent_kg_topics()` / `agent_kg_tasks()` give agent a map of its own state |

The result is a model that carries its own **semantically coherent, token-efficient, self-queryable memory** — and can explain what it remembers and why.

---

## Implementation Phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| 0 | Scaffold | `agent_kg` package via `/new-kg-module`; `AgentKGAdapter` stub in kgrag |
| 1 | Ingest | Phase 1 incremental parser; `Turn`, `Topic`, `Entity` nodes; SQLite + LanceDB |
| 2 | Query | `query()` / `pack()` / `assemble_context()` |
| 3 | Pruning | KG Context Pruning algorithm; `Summary` nodes; `prune()` |
| 4 | MCP | Full MCP tool surface; integration with KGRAG corpus |
| 5 | Agent loop | Self-invocation: agent automatically ingests its own turns |

---

## Resolved Design Decisions

### 1. Summarization Model — Configurable Dual-Backend

Pruning uses a configurable summarization backend. Default is the session's primary LLM (Claude API); an optional local endpoint supports Ollama-compatible servers for air-gapped or cost-sensitive deployments.

Configuration (in `agentkg.toml` or environment):

```toml
[summarizer]
backend = "primary"          # "primary" | "local"
local_endpoint = "http://localhost:11434/api/generate"
local_model = "llama3.2"
```

```python
class SummarizerConfig:
    backend: Literal["primary", "local"] = "primary"
    local_endpoint: str | None = None   # Ollama-compatible URL
    local_model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 512
```

The `primary` backend calls the same LLM driving the session — maximum coherence, best summarization quality. The `local` backend POSTs to the provided endpoint with an Ollama-compatible payload; no authentication by default. Switching backends mid-session is supported (e.g. fall back to local if primary rate-limits).

### 2. Pruning Granularity — Topic-Semantic Clustering

Cluster by topic proximity (cosine similarity over `Topic` node embeddings). Time is always recoverable from `Turn.timestamp` and `Turn.turn_index`, so there is no need for a structural time-window dimension — temporal ordering is a property of the data, not the clustering strategy.

Clustering algorithm: hierarchical agglomerative clustering with cosine distance, `threshold=0.25`. Each cluster must span ≥ 3 turns to be worth compressing.

### 3. Persistence — Split Storage by Scope

AgentKG uses **two storage locations** reflecting the two different scopes of what it knows:

```
~/.kgrag/
  registry.sqlite              # existing KG registry + PersonCorpusEntry
  profiles/
    <person_id>/
      userprofile.sqlite       # UserProfile graph (Preference, Expertise, Interest, Commitment)
      userprofile.lancedb/     # embeddings for profile nodes

<repo>/.agentkg/
  graph.sqlite                 # conversation tree only (Turn, Topic, Task, Summary)
  lancedb/                     # conversation embeddings
  snapshots/                   # temporal snapshots (same format as CodeKG/DocKG)
  sessions.jsonl               # session index: id, start_time, end_time, turn_count
```

**UserProfile** (`~/.kgrag/profiles/`) — global, permanent, cross-project. Survives repo deletion, `--wipe`, or any `.agentkg/` operation. One canonical profile regardless of which repo you're working in.

**Conversation tree** (`.agentkg/`) — repo-scoped, prunable, session-aware. Mirrors the `.codekg/` / `.dockg/` convention. `--wipe` clears conversation history for a fresh start without touching the UserProfile.

**Project-specific preferences** (e.g. "always use Poetry in this repo", "this codebase uses NumPy docstrings") are stored as `ProjectContext` nodes in the repo-scoped `.agentkg/` graph — not in the global UserProfile. The global profile provides defaults; local project context overrides them.

Session management:
- Each session gets a UUID and is recorded in `sessions.jsonl`
- `--wipe` clears the graph entirely (new project, fresh start)
- `--wipe-session SESSION_ID` removes a single session's turns while preserving summaries from prior pruning passes
- Between-session continuity is the default — the graph accumulates across the project lifetime

`kgrag init` auto-detects `.agentkg/` and registers the `agent` KG layer alongside `code` and `doc`.

### 4. Intent Classification — Full NLP Pipeline

Intent classification is a first-class citizen, not a heuristic afterthought. The pipeline:

**Stage 1 — Syntactic signals (spaCy):**
- Interrogative detection: sentence starts with aux-inversion or wh-word → `question`
- Imperative detection: root verb is base form with no subject → `request`
- Negation scope: negation token near root verb → `correction`
- Affirmative particles ("yes", "exactly", "right") → `confirmation`

**Stage 2 — Semantic classification (sentence-transformer + lightweight head):**
- Embed the sentence; classify against intent prototypes using cosine similarity
- Categories: `question` | `request` | `correction` | `confirmation` | `clarification` | `context` | `feedback`
- Confidence threshold: 0.75; below threshold → `unknown` (still stored, never silently dropped)

**Stage 3 — Task extraction:**
- Imperative sentences with a discernible object → candidate `Task` node
- Resolution detection: subsequent turns referencing the same entity + completion language → `RESOLVES` edge

The full pipeline runs in Phase 1, synchronously, before the graph update. spaCy `en_core_web_sm` is the default model (fast, no GPU required).

### 5. Privacy — Local-Only by Default

`.agentkg/` is added to `.gitignore` automatically on `kgrag init`. Conversational graphs are never committed, pushed, or included in snapshots unless the user explicitly opts in via `--include-agent` on snapshot commands.

The registry entry for an `agent` KG carries `metadata: {"private": true}` by default. KGRAG federated queries skip private KGs unless `--include-private` is passed.

---

## Revised Package Layout

```
agent_kg/
  src/agent_kg/
    __init__.py
    graph.py              # ConversationGraph: repo-scoped SQLite + LanceDB (.agentkg/)
    profile.py            # UserProfileGraph: user-scoped SQLite + LanceDB (~/.kgrag/profiles/)
    ingest.py             # Phase 1: sentence parse → NLP → conversation tree update
    nlp/
      intent.py           # Intent classification pipeline (spaCy + embeddings)
      entities.py         # Named entity extraction and deduplication
      topics.py           # Topic extraction and similarity-based merge
      preferences.py      # Preference/commitment/expertise extraction → UserProfile
    consolidate.py        # Phase 2: background re-embedding + edge refresh
    prune.py              # KG Context Pruning: cluster → summarize → rebuild
    summarize.py          # SummarizerBackend: primary LLM + local Ollama endpoint
    assemble.py           # Context assembly: summaries + recent + tasks + profile
    onboard.py            # Structured onboarding interview → UserProfile population
    session.py            # Session lifecycle: open/close/wipe/wipe-session
    snapshots.py          # Snapshot support for conversation tree (mirrors code_kg pattern)
    cli/
      main.py             # agent_kg ingest / query / prune / stats / session / onboard
    mcp/
      server.py           # MCP tool surface
```

---

## PersonCorpus: The Convergence Point

The `PersonCorpus` is the natural federation layer for everything KGRAG knows about a human. The physical split between UserProfile (user-scoped) and conversation tree (repo-scoped) is hidden behind the corpus abstraction — a single federated query traverses both transparently.

```
kgrag person create "Eric"
kgrag init ~/repos/kgrag --corpus person:Eric    # registers agent_kg, code_kg, doc_kg
kgrag init ~/repos/code_kg --corpus person:Eric
```

The resulting corpus, with storage locations made explicit:

```
PersonCorpus("Eric")
  │
  ├── ~/.kgrag/profiles/eric/userprofile   ← WHO Eric is          (global, permanent)
  │     Preference, Style, Expertise, Interest, Commitment
  │
  ├── <repo>/.agentkg/                     ← WHAT we're doing     (repo, prunable)
  │     Turn, Topic, Task, Summary, ProjectContext
  │
  ├── diary_kg                             ← WHAT Eric has lived  (temporal, append-only)
  ├── memory_kg                            ← WHAT Eric remembers  (persistent, curated)
  ├── code_kg/*                            ← WHAT Eric builds     (structural, versioned)
  └── doc_kg/*                             ← WHAT Eric references (semantic, versioned)
```

A single federated query across this corpus answers questions no individual KG can:

```bash
kgrag person query "Eric" "what does Eric care about most in code reviews?"
# → Searches: UserProfile preferences + diary entries + past conversation summaries
#   + memory facts + code commit patterns

kgrag person query "Eric" "what is Eric working on right now?"
# → Searches: open Task nodes in agent_kg + recent diary + active code_kg branches

kgrag person query "Eric" "what makes Eric laugh?"
# → Searches: Interest nodes in UserProfile + diary + conversation topics
```

### PersonCorpusEntry ↔ UserProfile Sync

`PersonCorpusEntry.metadata` is enriched from the UserProfile tree on each session close:

```python
# Auto-synced fields
entry.metadata["expertise"] = [n.label for n in profile.expertise_nodes]
entry.metadata["interests"] = [n.label for n in profile.interest_nodes]
entry.metadata["commitments"] = [n.label for n in profile.commitment_nodes]
entry.metadata["style_summary"] = profile.style_summary()   # LLM-generated one-liner
```

This means `kgrag person info "Eric"` shows a live summary of the user's preferences and expertise without needing to query the full AgentKG.

---

## Updated Implementation Phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| 0 | Scaffold | `agent_kg` package via `/new-kg-module`; `AgentKGAdapter` stub in kgrag |
| 1 | Conversation tree | Phase 1 incremental parser; `Turn`, `Topic`, `Entity` nodes; SQLite + LanceDB |
| 2 | Query + assembly | `query()` / `pack()` / `assemble_context()` |
| 3 | Pruning | KG Context Pruning; `Summary` nodes; `prune()` |
| 4 | UserProfile tree | `Preference`, `Style`, `Interest`, `Expertise`, `Commitment` nodes; implicit learning |
| 5 | Onboarding skill | `/onboard` structured interview; NLP extraction → UserProfile |
| 6 | PersonCorpus sync | `kgrag person` integration; metadata sync on session close |
| 7 | MCP + agent loop | Full MCP surface; agent self-ingests its own turns |

---

## The Bigger Picture

Each KGModule indexes a different *kind of knowledge*:

| Module | What it knows |
|--------|--------------|
| CodeKG | The structure of *code* |
| DocKG | The structure of *documentation* |
| DiaryKG | The structure of *lived experience* |
| MemoryKG | The structure of *remembered facts* |
| AgentKG | The structure of *this conversation* + *who you are* |

The `PersonCorpus` federates all of them into a single queryable model of a human being — their knowledge, their history, their preferences, their current work, their open commitments.

AgentKG's UserProfile tree is the piece that was always missing: a structured, machine-readable, continuously updated model of the *person the agent is talking to*. Not a flat preferences file. Not a system prompt. A live knowledge graph that grows richer with every interaction and never forgets.

This is not a memory hack. It is not a RAG band-aid. It is a new primitive: **agent cognition as a first-class knowledge graph**, symmetric with the graphs used to represent code, documents, and lived human experience.

The architecture is not clever. It is *correct*.
