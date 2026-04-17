# Patent Application

**AGENT COGNITION AS KNOWLEDGE GRAPH: DYNAMIC MEMORY, CONTEXT PRUNING, AND CONVERSATIONAL LEARNING FOR AUTONOMOUS LLM SYSTEMS**

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

This application may be filed concurrently with or after U.S. Patent Application No. [PENDING-1], entitled "Deterministic Knowledge Compilation from Formally-Structured Source Artifacts with Hybrid Structural-Semantic Retrieval and Provenance-Grounded Synthesis," and U.S. Patent Application No. [PENDING-2], entitled "System and Method for Federated Retrieval-Augmented Generation over Structurally Derived Heterogeneous Knowledge Graphs."

In a preferred embodiment described in Section X below, conversational knowledge graphs constructed by the present invention are registered with the federated retrieval system described in [PENDING-2], enabling unified queries spanning conversational memory, code knowledge, documentation knowledge, and other domain-specific knowledge graphs. However, the present invention is independent of [PENDING-2] and may be practiced with any knowledge graph representation, storage mechanism, or query interface.

---

## STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

---

## FIELD OF THE INVENTION

The present invention relates to artificial intelligence systems, and more particularly to methods and systems for maintaining, managing, and leveraging conversational memory in large language model agents through dynamic knowledge graph construction, semantic compression, and context-aware assembly.

---

## BACKGROUND OF THE INVENTION

### The Context Window Problem

Large language models (LLMs) operate within a fixed context window—a bounded amount of token-based memory into which all prior conversation, instructions, and retrieved knowledge must fit. For finite conversations and single-turn queries, this is not a limitation. For extended multi-turn agent interactions, context management becomes the primary challenge.

Two failure modes emerge as conversations extend:

**First, truncation rot.** When a conversation exceeds the context window size, the oldest content is silently dropped. Early decisions, established facts, constraints, and commitments disappear without warning. The agent cannot reason about why certain decisions were made, what constraints were established, or what commitments remain open. This is not a bug in the implementation—it is a structural property of the fixed-size token buffer.

**Second, diffusion rot.** Even before truncation, as context grows longer, the relevance signal diffuses. The model must allocate its attention (its learned capacity to focus) across an increasingly large set of utterances. Material near the beginning of the conversation receives proportionally less attention weight than material near the end. The agent "forgets" earlier context not by dropping it, but by attending to it less.

### Prior Art and Limitations

Existing mitigations fall into three categories, all of which have fundamental limitations.

**Summarization approaches** maintain a running summary of the conversation, appending it to each new prompt and truncating older messages. Summaries are lossy—they discard details, nuance, and explicit commitments in favor of topical overviews. Once information is summarized, it cannot be recovered with precision. Furthermore, summaries are static—once created, they are not recomputed or adjusted as new context arrives, leading to stale or contextually inappropriate summaries later in the conversation.

**Retrieval-augmented generation (RAG) approaches** retrieve relevant prior utterances or summaries based on semantic similarity to the current query. This addresses diffusion rot by selecting context semantically rather than positionally. However, RAG systems:
- Rank by global semantic proximity, which does not account for structural relationships (dependencies, causal chains, temporal ordering)
- Return document chunks or summaries, not the underlying structured facts
- Have no mechanism to ensure that open commitments, pending tasks, or established constraints are preserved in retrieval
- Provide no way for the agent to introspect what it "knows" about the conversation or to explain its memory

**Agent memory files** (e.g., a shared JSON file or vector store updated by the agent) require the agent to explicitly decide what to remember and how to update it. This places the burden of memory management on the agent itself and provides no principled mechanism for deciding what to retain, what to compress, or what to discard.

### The Root Insight

The fundamental insight is that **conversation is not a list of messages—it is a graph of topics, intents, entities, decisions, and their relationships through time**. Representing it as a flat string wastes the structure already implicit in the dialogue.

What is needed is a system that:
1. Represents conversational state as a **live, queryable knowledge graph** updated on every turn
2. Manages growth through **semantic compression**, not lossy summarization
3. Assembles context **dynamically and semantically**, not by position or truncation
4. Exposes the agent's memory as a **queryable first-class primitive**, enabling the agent to ask "what do I know about X?" and get structured answers
5. Preserves **user preferences, expertise, and commitments** in a persistent, evolving model of the person the agent is speaking to
6. Provides **hierarchical, lossless compression** where old conversational turns are folded into semantic summaries that can themselves be compressed in subsequent passes

The present invention provides such a system.

---

## SUMMARY OF THE INVENTION

The present invention provides a conversational knowledge graph system, termed AgentKG, comprising a live graph representation of conversational state, an incremental ingestion pipeline that updates the graph on every turn, a semantic compression algorithm called KG Context Pruning that reduces graph size while preserving semantic coherence, a dynamic context assembly mechanism that retrieves and orders context for downstream model synthesis, a persistent user profile graph that evolves across sessions, and a query interface enabling the agent to introspect its own memory.

### Core Components

**Conversational Knowledge Graph**: A persistent graph data structure storing `Turn`, `Topic`, `Intent`, `Entity`, `Task`, and `Summary` node types, connected by temporal, semantic, and structural edges. The graph grows monotonically through each conversation turn and is compressed periodically through pruning passes.

**Incremental Ingestion Pipeline**: A lightweight NLP pipeline that executes on every incoming user message, extracting named entities, topics, intents, and task mentions via syntactic and semantic analysis, deduplicating against existing nodes, and updating the graph in real time. The pipeline runs synchronously and completes within a small bounded time independent of graph size.

**KG Context Pruning Algorithm**: A semantic compression algorithm that, when triggered by graph size or token budget thresholds, identifies cold (old) subgraphs, clusters them by topic proximity using cosine similarity, summarizes each cluster via language model, creates `Summary` nodes encoding the compressed content, rewires edges to preserve traversability, and removes the original nodes. The algorithm is iterative—summaries from one pruning pass can themselves be pruned in a subsequent pass, creating hierarchical compression.

**Dynamic Context Assembly**: A retrieval and ranking mechanism that, given a query and a token budget, assembles context by combining semantic retrieval over the graph, preservation of recent verbatim turns, inclusion of all open tasks and commitments, and user profile information, respecting the token budget constraint.

**User Profile Graph**: A separate, persistent knowledge graph storing `Preference`, `Style`, `Interest`, `Expertise`, and `Commitment` nodes representing the user's characteristics, preferences, and commitments. The profile is never pruned and is populated both by explicit onboarding and through implicit learning from conversation turns.

**Query and Introspection Interface**: Methods enabling the agent to query its own conversational memory, list topics and tasks, and retrieve context assembled for a given query, making the agent's memory transparent and queryable.

---

## BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 is a system architecture diagram illustrating the layered components of AgentKG, showing the incremental ingestion pipeline, the graph storage layer, the semantic index layer, the pruning subsystem, and the context assembly layer.

FIG. 2 is a data structure diagram illustrating the conversational graph schema, showing node kinds (`Turn`, `Topic`, `Intent`, `Entity`, `Task`, `Summary`) and edge types (`FOLLOWS`, `ADDRESSES`, `EXPRESSES`, `MENTIONS`, `CREATES`, `RESOLVES`, `RELATED_TO`, `COMPRESSED_INTO`).

FIG. 3 is a flow diagram illustrating the incremental ingestion pipeline, showing sentence parsing, NLP extraction, deduplication, graph update, and embedding stages.

FIG. 4 is a flow diagram illustrating the KG Context Pruning algorithm, showing cold subgraph identification, topic-semantic clustering, LLM summarization, `Summary` node creation, edge rewiring, and original node removal.

FIG. 5 is a conceptual diagram illustrating the difference between standard conversation memory (flat message list) and AgentKG (structured graph with semantic edges), showing how structural relationships enable correct retrieval without semantic similarity.

FIG. 6 is a data flow diagram illustrating the dynamic context assembly process, showing semantic retrieval seeding, recent turn preservation, task inclusion, and token budget enforcement.

FIG. 7 is a diagram illustrating the two-tree storage model, showing the conversation tree (repo-scoped, prunable) and the UserProfile tree (user-scoped, persistent).

FIG. 8 is a timeline diagram illustrating pruning passes over a conversation, showing original turns compressed into summaries, summaries compressed into second-level summaries, and the temporal ordering preserved through turn indices.

---

## DETAILED DESCRIPTION OF THE INVENTION

The following detailed description sets forth specific embodiments of the invention with reference to the accompanying figures. Like reference numerals refer to like elements throughout.

### I. THE AGENT COGNITION PROBLEM

The context window constraint is not a flaw that can be engineered away. It is inherent to the token-based attention mechanism at the heart of transformer architectures. Given this constraint, the agent must choose: either (a) truncate older context, losing information; (b) summarize older context, losing precision; or (c) represent conversation as a queryable structure, preserving information and enabling semantic retrieval.

The present invention pursues option (c). The key insight is that an agent's memory should be symmetric to the knowledge graphs used to represent other domains (code, documents, biochemical pathways). Just as a codebase can be represented as a knowledge graph with structural and semantic properties, a conversation can be represented the same way.

This symmetry enables a new capability: **federated queries spanning the agent's conversational memory, the code it is working with, the documentation it references, and the domain-specific knowledge it consults**, all through a single uniform retrieval interface.

### II. CONVERSATIONAL GRAPH SCHEMA

Referring to FIG. 2, the conversational knowledge graph comprises seven node kinds and eight edge types.

**Node Kinds**

| Kind | Purpose | Key Fields |
|------|---------|------------|
| `Turn` | One user or agent message | `role` (user/agent), `text`, `timestamp`, `turn_index`, `token_count` |
| `Topic` | A subject being discussed | `label`, `canonical_form`, `first_seen_turn`, `last_seen_turn` |
| `Intent` | What the user is trying to accomplish | `label`, `category` (question/request/correction/confirmation/clarification/context/feedback), `confidence` |
| `Entity` | A named thing mentioned | `label`, `kind` (file/function/concept/person/project/tool), `source_turn` |
| `Task` | A concrete action requested or to be completed | `description`, `status` (open/in_progress/completed/abandoned), `created_turn`, `resolved_turn` |
| `Summary` | A compression of a pruned subgraph | `text`, `covers_turns` (array of turn indices), `created_at`, `pruning_pass`, `topic_coverage` (array of topic labels) |
| `UserProfileNode` | (in UserProfile tree) Preference, Style, Interest, Expertise, or Commitment | `kind`, `label`, `category`, `updated_at`, `learned_implicitly` (boolean) |

**Edge Types**

| Relation | From → To | Meaning | Evidence |
|----------|-----------|---------|----------|
| `FOLLOWS` | Turn → Turn | Temporal sequence | turn indices |
| `ADDRESSES` | Turn → Topic | This turn discusses this topic | NLP extraction + cosine similarity |
| `EXPRESSES` | Turn → Intent | This turn carries this intent | intent classification |
| `MENTIONS` | Turn → Entity | This entity appears in this turn | NER extraction |
| `CREATES` | Turn → Task | This turn initiates a task | imperative parsing |
| `RESOLVES` | Turn → Task | This turn completes or closes a task | task completion detection |
| `RELATED_TO` | Topic ↔ Topic | Semantic proximity between topics | cosine similarity > threshold |
| `COMPRESSED_INTO` | Turn → Summary | This turn was folded into a summary node | pruning pass metadata |

All nodes carry the following properties:
- `node_id`: Stable UUID
- `created_at`: ISO 8601 UTC timestamp
- `embedding`: Dense vector (384-dim, sentence-transformer)
- `pruning_pass`: Integer (0 = original, N = survived N pruning passes; null for UserProfile nodes)

### III. INCREMENTAL INGESTION PIPELINE

Referring to FIG. 3, the incremental ingestion pipeline executes synchronously on every incoming user message and completes in time independent of graph size.

**Stage 1: Sentence Tokenization and NLP Extraction**

The input text is tokenized into sentences using a lightweight NLP model (spaCy `en_core_web_sm` in the preferred embodiment). For each sentence:

1. **Named Entity Recognition**: A spaCy named entity recognizer extracts entities (PERSON, ORG, PRODUCT, GPE, etc.) and maps them to candidate `Entity` nodes. For each entity, a kind is assigned from the enumerated set {file, function, concept, person, project, tool, location, other}.

2. **Noun Chunk and Verb Phrase Extraction**: Noun chunks and verb phrases are extracted as candidate topics. Each candidate is a string label.

3. **Intent Classification**: The sentence is classified as expressing one of seven intents via a two-stage classifier:
   - **Stage A (syntactic signals)**: Interrogative sentences (aux inversion, wh-words) → `question`; imperative sentences (base-form verb, no subject) → `request`; negation scope near root verb → `correction`; affirmative particles → `confirmation`.
   - **Stage B (semantic signals)**: The sentence is encoded as a dense vector using a sentence transformer model; the vector is compared via cosine similarity to prototype vectors for each intent category; the highest-similarity intent is selected if similarity ≥ 0.75, else `unknown`.

4. **Task Extraction**: Sentences classified as `request` with a discernible object (direct or prepositional object) are marked as potential task creation turns.

**Stage 2: Deduplication Against Existing Nodes**

For each extracted topic and entity:

1. Compute cosine similarity between the new node's embedding and all existing nodes of the same kind in the graph.
2. If max similarity ≥ 0.88, select the highest-similarity existing node as a merge target.
3. If max similarity < 0.88, create a new node.

This deduplication prevents topic proliferation and keeps semantically identical topics grouped under a canonical node.

**Stage 3: Graph Update**

A `Turn` node is created with the incoming text, role, timestamp, and turn index. Then:

1. A `FOLLOWS` edge is added from the previous turn (if one exists) to the new turn.
2. For each extracted topic, add an `ADDRESSES` edge from the turn to the topic (or merged canonical topic).
3. For each extracted intent, add an `EXPRESSES` edge from the turn to an `Intent` node (creating it if new).
4. For each extracted entity, add a `MENTIONS` edge from the turn to the entity (or merged canonical entity).
5. If a task is identified as newly created, create a `Task` node with status `open` and add a `CREATES` edge from the turn.
6. If a task is identified as resolved (linguistic signals: completion words, past tense, explicit closure), find the matching `Task` node and update its status to `completed`, add a `RESOLVES` edge from the current turn to the task.
7. Update `last_seen_turn` on all touched topic nodes.

**Stage 4: Semantic Indexing**

The turn text and all newly created/merged node texts are encoded as dense vectors using a sentence transformer model (e.g., `all-MiniLM-L6-v2`, 384-dimensional). These vectors are stored in a vector database (LanceDB in the preferred embodiment) associated with each node's UUID.

This stage is marked as non-blocking and can execute asynchronously without delaying the next turn.

### IV. KG CONTEXT PRUNING: SEMANTIC COMPRESSION

Referring to FIG. 4, KG Context Pruning is the core innovation enabling unbounded conversation without information loss.

**Trigger Conditions**

Pruning is triggered when any of the following conditions holds:

1. **Turn count**: The number of original (non-summary) `Turn` nodes exceeds 30.
2. **Token budget**: The estimated token count of the graph (computed as sum of all node text lengths × 4/3) exceeds 60% of the downstream model's context window.
3. **Explicit invocation**: The user or agent invokes pruning via `agent_kg prune --budget TOKENS`.
4. **Pre-retrieval**: Automatically triggered before context assembly if the graph exceeds budget.

**Algorithm**

```
def prune(graph, model, token_budget):
    # 1. Identify cold subgraph
    # Cold = turns with turn_index < (current_turn_index - WINDOW)
    # where WINDOW = 20 (configurable)
    cold_turns = [t for t in graph.turns if t.turn_index < graph.current_turn - WINDOW]
    cold_nodes = cold_turns + {t in topic_nodes, entity_nodes, task_nodes
                                if t.last_seen_turn in cold_turns}
    cold_graph = graph.subgraph(cold_nodes)

    # 2. Cluster by topic proximity
    # Build topic affinity matrix: rows/cols = Topic nodes in cold_graph
    # affinity[i][j] = cosine_similarity(topic[i].embedding, topic[j].embedding)
    # Apply hierarchical agglomerative clustering with threshold 0.25
    clusters = hac(cold_graph.topics, distance_metric='cosine', threshold=0.25)

    # Filter: keep only clusters with ≥ 3 turns
    clusters = [c for c in clusters if len(c.turns) >= 3]

    for cluster in clusters:
        # 3. Extract cluster text
        # Concatenate turn texts in temporal order
        texts = [t.text for t in sorted(cluster.turns, key=lambda t: t.turn_index)]
        context = "\n\n".join(texts)

        # 4. Summarize via LLM
        # System prompt: "You are summarizing a conversation segment.
        #                 Preserve all decisions, facts, questions, and commitments.
        #                 Do not lose information."
        summary_text = model.generate(
            messages=[
                {"role": "user", "content":
                    f"Summarize this conversation, preserving all decisions, facts, and commitments:\n\n{context}"}
            ],
            temperature=0.2,
            max_tokens=512
        ).text

        # 5. Create Summary node
        summary_node = SummaryNode(
            text=summary_text,
            covers_turns=[t.id for t in cluster.turns],
            covers_topics=[tc.id for tc in cluster.topics],
            pruning_pass=graph.pruning_pass + 1,
            embedding=embed(summary_text)
        )
        graph.add_node(summary_node)

        # 6. Rewire edges
        # For each Topic in the cluster, add EXPANDS edge from summary
        for topic in cluster.topics:
            graph.add_edge(summary_node, topic, rel='EXPANDS')

        # For each Entity mentioned in cluster turns, add EXPANDS edge
        for entity in cluster.entities:
            graph.add_edge(summary_node, entity, rel='EXPANDS')

        # For each Task created or resolved in cluster, preserve CREATES/RESOLVES edges
        # but also add EXPANDS edge from summary to task
        for task in cluster.tasks:
            graph.add_edge(summary_node, task, rel='EXPANDS')

        # 7. Remove original nodes
        # Delete all Turn nodes in the cluster
        # Delete all intermediate Topic/Entity nodes that are not connected to
        # non-cold parts of the graph
        graph.remove(cluster.turns)

    graph.pruning_pass += 1
    graph.last_pruned_at = now()
    return graph
```

**Properties of Pruned Graphs**

- **Lossless semantics**: The summary captures decisions, facts, and open questions; not a topic label or headline.
- **Composability**: Summaries can themselves be pruned in a second pass, creating hierarchical compression. A second-level summary summarizes summaries.
- **Traversability**: The `EXPANDS` edges allow reconstruction of what topics and entities a summary covers. Walking the graph backwards recovers the original conversation structure.
- **Temporal preservation**: Turn indices are preserved in `covers_turns` metadata, so the timeline is always recoverable.
- **Comparability**: The embedding distance between `Summary` nodes reveals topic drift and coherence.

**Iterative Compression**

When a second pruning pass is triggered, the algorithm operates the same way, but now summaries from the first pass can be merged and re-summarized. A summary covering turns 1-20 and a summary covering turns 21-40 can be identified as semantically related (via `RELATED_TO` edges computed on their embeddings) and combined into a single higher-level summary covering turns 1-40. This process can repeat, creating a pyramid of summaries covering increasingly large time windows.

### V. DYNAMIC CONTEXT ASSEMBLY

Referring to FIG. 6, dynamic context assembly is the mechanism by which the agent retrieves context for the language model without truncation or diffusion.

**Algorithm**

```
def assemble_context(graph, query, token_budget):
    # 1. Semantic retrieval seeding
    # Encode query as dense vector
    query_vector = embed(query)

    # Retrieve k=8 most similar nodes (across all kinds)
    seed_nodes = graph.vector_index.knn(query_vector, k=8)

    # 2. Temporal spine preservation
    # Always include the most recent N turns (default N=5)
    recent_turns = graph.turns[-5:]

    # 3. Open commitment preservation
    # Retrieve all Task nodes with status='open'
    open_tasks = [t for t in graph.tasks if t.status == 'open']

    # 4. User profile injection
    # If available, retrieve user profile context
    profile_nodes = []
    if graph.user_profile:
        profile_relevant = graph.user_profile.query(query, k=3)
        profile_nodes = profile_relevant

    # 5. Pack into token budget
    # Order: recent turns (verbatim) → open tasks → semantic matches → profile
    # Stop when token count exceeds budget
    context_parts = []
    token_count = 0

    # Add recent turns (highest priority)
    for turn in recent_turns:
        turn_tokens = estimate_tokens(turn.text)
        if token_count + turn_tokens <= token_budget:
            context_parts.append(("turn", turn))
            token_count += turn_tokens

    # Add open tasks
    for task in open_tasks:
        task_tokens = estimate_tokens(task.description)
        if token_count + task_tokens <= token_budget:
            context_parts.append(("task", task))
            token_count += task_tokens

    # Add semantic matches
    for node in seed_nodes:
        node_tokens = estimate_tokens(node.text)
        if token_count + node_tokens <= token_budget:
            context_parts.append(("semantic_match", node))
            token_count += node_tokens

    # Add profile if room
    for pnode in profile_nodes:
        pnode_tokens = estimate_tokens(pnode.text)
        if token_count + pnode_tokens <= token_budget:
            context_parts.append(("profile", pnode))
            token_count += pnode_tokens

    # 6. Format as Markdown
    markdown = format_context_markdown(context_parts, graph)
    return markdown, token_count
```

**Context Ordering and Formatting**

The assembled context is formatted as a Markdown document with sections:

```markdown
## Recent Conversation

[Most recent 5 turns, verbatim, in temporal order]

## Open Tasks

[All open Task nodes with descriptions and creation turns]

## Relevant Context

[Semantic matches, ordered by relevance score]

## User Profile

[User preferences, expertise, interests, commitments]
```

This structure ensures that:
- **Recent context is always available** and not diluted by older material
- **Open commitments are never forgotten**
- **Semantic retrieval finds relevant context** regardless of age
- **User preferences are visible** and inform the agent's response

### VI. USER PROFILE GRAPH

The UserProfile graph is a separate, persistent graph stored in user space (`~/.kgrag/profiles/<person_id>/`) rather than repo space. It represents the user as a structured entity with preferences, expertise, interests, and commitments.

**Node Kinds**

| Kind | Purpose | Examples |
|------|---------|----------|
| `Preference` | An expressed preference or constraint | "prefer type annotations", "verbosity: concise", "always run tests" |
| `Style` | A coding or communication style trait | "docstrings: Google style", "no trailing comments" |
| `Interest` | A personal interest or hobby | "sailing", "computational biology", "jazz" |
| `Expertise` | A domain of deep knowledge | "Python", "metabolic pathways", "knowledge graphs" |
| `Commitment` | A standing instruction or rule | "always run ruff before committing", "never use --no-verify without asking" |

**Edge Types**

| Relation | Meaning |
|----------|---------|
| `PREFERS` | UserProfile → Preference/Style |
| `INTERESTED_IN` | UserProfile → Interest |
| `EXPERT_IN` | UserProfile → Expertise |
| `COMMITTED_TO` | UserProfile → Commitment |
| `UPDATED_BY` | Turn → Preference (metadata edge, turn_id field) |
| `CONFLICTS_WITH` | Preference ↔ Preference (detected contradictions) |

**Lifecycle**

- **Created**: Agent Onboarding Skill at first session, or explicit `kgrag person create` command
- **Updated**: Any conversation turn that expresses a preference, correction, or personal context triggers creation or update
- **Never pruned**: UserProfile nodes survive all pruning passes
- **Persistent**: Survives repo deletion, `.agentkg/ --wipe`, branch changes

**Implicit Learning**

While explicit onboarding populates the initial profile, the agent learns implicitly through the conversation:

- User says "I prefer type annotations" → create/update `Preference` node
- User says "stop doing X" → update or invert a `Commitment`
- User says "I'm learning about metabolic pathways" → create `Expertise` node with `learned_implicitly=True`

Each learning event creates an `UPDATED_BY` edge from the turn to the modified node, preserving provenance.

### VII. FEDERATED INTEGRATION

In a preferred embodiment, the conversational knowledge graph is registered as a new knowledge graph kind (`KGKind.AGENT`) and integrated with the federated retrieval system described in Section II of [PENDING-2].

**AgentKGAdapter**

An `AgentKGAdapter` class implementing the uniform adapter interface enables the conversational graph to participate in federated queries:

```python
class AgentKGAdapter(KGAdapter):
    """Adapter wrapping AgentKG conversational memory."""

    _kind = KGKind.AGENT

    def is_available(self) -> bool:
        """Return True if .agentkg/ exists and contains a graph."""

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Semantic query over conversation graph."""

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Extract context snippets for LLM injection."""

    def stats(self) -> dict:
        """Return node_count, edge_count, pruning_pass, topic_count, task_count."""

    def analyze(self) -> str:
        """Return Markdown analysis report of conversation."""

    # AgentKG-specific extensions
    def ingest(self, turn: Turn) -> None:
        """Phase 1 incremental update."""

    def prune(self, token_budget: int | None = None) -> PruneReport:
        """Trigger KG Context Pruning."""

    def assemble_context(self, query: str, budget: int) -> str:
        """Return assembled context as Markdown."""

    def list_tasks(self, status: str | None = None) -> list[Task]:
        """List tasks, optionally filtered by status."""

    def list_topics(self, min_recency: int = 0) -> list[Topic]:
        """List topics with recency and salience scores."""
```

When registered with the KGRAG federation layer, a federated query can span conversational memory, code, documentation, diary entries, and other knowledge graphs simultaneously:

```bash
kgrag person query "Eric" "What have we been working on recently and what's my opinion on type safety?"
# → Returns results from:
#   - agent_kg: recent turns and summaries mentioning type safety
#   - code_kg: recent code commits referencing type annotations
#   - diary_kg: recent entries mentioning work
#   - UserProfile: expertise in Python, preference for type annotations
```

### VIII. MCP SERVER INTEGRATION

The system exposes an MCP (Model Context Protocol) server that makes AgentKG queryable as a set of callable tools for AI agent clients.

**Tool Surface**

| Tool | Signature | Purpose |
|------|-----------|---------|
| `agent_kg_ingest` | `(turn_text: str, role: str) -> TurnNode` | Add a turn and update graph |
| `agent_kg_query` | `(q: str, k: int = 8) -> list[CrossHit]` | Semantic search |
| `agent_kg_pack` | `(q: str, budget: int = 4000) -> str` | Assemble context |
| `agent_kg_prune` | `(budget: int \| None) -> PruneReport` | Trigger pruning |
| `agent_kg_tasks` | `(status: str \| None) -> list[Task]` | List tasks |
| `agent_kg_topics` | `() -> list[Topic]` | List topics with stats |
| `agent_kg_stats` | `() -> RegistryStats` | Node/edge counts |

### IX. COMPARISON TO PRIOR ART

| Approach | Truncation rot | Diffusion rot | Lossy? | Queryable? | Self-aware? |
|----------|---|---|---|---|---|
| Sliding window (drop old) | ❌ | ❌ | ✓ | ❌ | ❌ |
| Summarization | Partial | Partial | ✓ | ❌ | ❌ |
| RAG retrieval | ✓ | ✓ | ✗ (chunks) | ✓ | ❌ |
| **AgentKG** | ✓ | ✓ | ✗ (lossless) | ✓ | ✓ |

AgentKG is the only approach that:
- Prevents truncation through lossless compression
- Prevents diffusion through semantic (not positional) retrieval
- Preserves information completely
- Enables queries into memory
- Makes memory self-introspectable

### X. ALTERNATIVE EMBODIMENTS

In alternative embodiments, the graph storage layer may use a graph database such as Neo4j or ArangoDB in place of SQLite, with adaptations to the graph update and pruning operations.

In alternative embodiments, the sentence transformer model may be replaced by any model producing fixed-dimensional dense vectors, including domain-specific fine-tuned models.

In alternative embodiments, the NLP pipeline may use alternative frameworks such as NLTK, transformer-based models (e.g., spacy-transformers), or custom trained classifiers for intent detection.

In alternative embodiments, the summarization backend may use any language model, including local models via Ollama, API-based models, or fine-tuned models.

In alternative embodiments, the federated integration described in Section VII may be omitted, with AgentKG operating as a standalone system.

---

## CLAIMS

**Claim 1.**
A computer-implemented system for managing conversational memory in large language model agents, the system comprising:
  one or more processors; and
  one or more non-transitory computer-readable media storing instructions that, when executed, cause the processors to perform:
    maintaining a persistent directed graph storing node records of a plurality of node kinds comprising `Turn` nodes representing user or agent messages, `Topic` nodes representing subjects under discussion, `Intent` nodes representing intended actions or questions, `Entity` nodes representing named entities, `Task` nodes representing requested or committed actions, and `Summary` nodes representing compressed subgraphs;
    for each node, storing a stable unique identifier, a kind label, canonical text, a dense vector embedding, creation timestamp, and optional metadata fields;
    receiving an incoming message from a user;
    executing a natural language processing pipeline that extracts named entities, noun phrases, intents, and tasks from the message without requiring a generative language model;
    deduplicating extracted entities and topics against existing nodes using cosine similarity over pre-computed embeddings, with a threshold of 0.88;
    creating a new `Turn` node for the incoming message and adding directed edges representing temporal sequence, topic mention, intent expression, and entity reference to corresponding node records;
    computing a dense vector embedding for the turn text using a sentence transformer model;
    storing the embedding in a co-located vector database indexed by node identifier;
    responsive to a trigger condition comprising any of: turn count exceeding 30, estimated token count exceeding 60% of a configured context window, or explicit invocation, executing a KG Context Pruning algorithm comprising:
      identifying a cold subgraph comprising `Turn` nodes with turn index less than a configured window;
      clustering Topic nodes in the cold subgraph by topic affinity using hierarchical agglomerative clustering with cosine distance metric and threshold 0.25;
      for each cluster containing three or more turns, concatenating the text of all turns in temporal order;
      generating a summary of the concatenated text using a language model;
      creating a new `Summary` node storing the generated summary text, the list of turn indices covered, and the cluster's semantic content;
      adding directed edges of relation type `EXPANDS` from the summary node to all Topic and Entity nodes mentioned in the cluster;
      removing the original Turn nodes from the graph;
    responsive to a query string and a token budget, executing a context assembly operation comprising:
      encoding the query string as a dense vector;
      retrieving the k nearest nodes from the vector database by cosine similarity, where k defaults to eight;
      including all `Task` nodes with status `open` in the result set;
      including the most recent N turn nodes, where N defaults to five;
      packing the retrieved nodes into a formatted context string that does not exceed the token budget;
      returning the formatted context string for injection into a language model prompt.

**Claim 2.**
The system of claim 1, further comprising storing a separate UserProfile graph in user-scoped persistent storage comprising `Preference`, `Style`, `Interest`, `Expertise`, and `Commitment` nodes representing persistent characteristics of the user, never subjecting UserProfile nodes to pruning, and enriching the UserProfile graph through implicit learning: when a conversation turn expresses a user preference, creates an edge from the turn to the corresponding UserProfile node with relation type `UPDATED_BY`, and updates the node's value and `updated_at` timestamp.

**Claim 3.**
The system of claim 1, wherein the KG Context Pruning algorithm is iterative: when a second pruning pass is triggered, Summary nodes created in a first pruning pass are eligible for clustering and re-summarization in the second pass, creating hierarchical summaries covering progressively larger time windows.

**Claim 4.**
The system of claim 1, wherein the context assembly operation orders retrieved nodes in the priority sequence: recent Turn nodes (verbatim), open Task nodes, semantic matches, UserProfile nodes; stops adding nodes when the token count would exceed the token budget; and formats the result as a Markdown document with section headers indicating the source and relevance of each component.

**Claim 5.**
The system of claim 1, wherein the NLP pipeline comprises:
  a sentence tokenization stage that splits the input message into sentences;
  a named entity recognition stage that extracts entities using a spaCy model and assigns a kind from {file, function, concept, person, project, tool, location, other};
  a noun chunk extraction stage that identifies candidate topics;
  a first-stage intent classification using syntactic signals: interrogative word order → `question`, imperative form → `request`, negation scope → `correction`, affirmative particles → `confirmation`;
  a second-stage intent classification that encodes the sentence as a dense vector, compares via cosine similarity to prototype vectors for each intent category, and selects the highest-similarity intent if similarity ≥ 0.75, else `unknown`.

**Claim 6.**
The system of claim 1, wherein the stable unique identifier for each node is constructed as a content-addressable UUID assigned at node creation and preserved across pruning passes for turn and task nodes.

**Claim 7.**
The system of claim 1, wherein the graph storage layer persists node records and edge records in a relational database, the preferred embodiment being SQLite with a schema comprising a `nodes` table storing node_id, kind, text, created_at, pruning_pass, and embedding_id, and an `edges` table storing source_id, relation, destination_id, and optional evidence fields.

**Claim 8.**
The system of claim 1, wherein the semantic index layer stores dense vectors in a vector database co-located with the relational database, the preferred embodiment being LanceDB, indexed by node_id with support for k-nearest-neighbor queries returning node identifiers and cosine similarity scores.

**Claim 9.**
The system of claim 1, wherein conversational knowledge graph instances can be registered as a new knowledge graph kind (`agent`) in a federated retrieval system, enabling unified queries spanning conversational memory, code knowledge graphs, documentation knowledge graphs, and other domain-specific knowledge graphs, with results globally ranked and returned with per-result source provenance.

**Claim 10.**
The system of claim 1, further comprising:
  a query interface exposing the conversational graph as queryable tools:
    a method `list_topics()` returning all Topic nodes with recency scores and salience metrics;
    a method `list_tasks(status)` returning Task nodes optionally filtered by status;
    a method `assemble_context(query, budget)` executing the context assembly algorithm and returning formatted Markdown;
  whereby the agent can introspect its own memory and retrieve context without explicit user management.

**Claim 11.**
A computer-implemented method for compressing a conversational knowledge graph without information loss, the method comprising:
  maintaining a directed graph of conversation turns, topics, entities, tasks, and summaries, with each turn assigned a monotonically increasing turn index and each node assigned a dense vector embedding;
  identifying a cold subgraph comprising all Turn nodes with turn index less than (current_turn_index - WINDOW), where WINDOW is a configurable integer defaulting to 20;
  constructing an affinity matrix of cosine similarities between all Topic nodes in the cold subgraph;
  partitioning the affinity matrix using hierarchical agglomerative clustering with distance metric cosine and linkage threshold 0.25;
  filtering the resulting clusters to retain only clusters with three or more constituent turns;
  for each retained cluster:
    extracting the text of all turns in the cluster;
    generating a summary of the extracted text using a language model, with instruction to preserve all decisions, facts, questions, and commitments;
    creating a Summary node storing the generated summary text, the set of turn indices covered, and metadata indicating the pruning pass;
    rewiring edges to add relations of type `EXPANDS` from the summary node to all Topic and Entity nodes that appear in the clustered turns;
    removing the original Turn nodes from the graph;
  incrementing a pruning_pass counter on the graph;
  whereby the graph shrinks by removing old turns while preserving their semantic content in Summary nodes, and the original turn structure remains recoverable through edge traversal.

**Claim 12.**
The method of claim 11, wherein Summary nodes created in a first pruning pass are themselves eligible for clustering and re-summarization in a second pruning pass, with the second pass receiving Summary nodes as input and producing higher-order Summary nodes that cover progressively larger time windows.

**Claim 13.**
The method of claim 11, wherein the clustering algorithm is configured with a threshold of 0.25, meaning two Topic nodes are in the same cluster if their cosine similarity exceeds 0.75 (complement of 0.25 distance).

**Claim 14.**
The method of claim 11, wherein the language model used for summarization is configurable: a primary backend uses the same language model driving the agent session; an alternative backend routes summarization requests to a local endpoint compatible with the Ollama API, enabling air-gapped or cost-sensitive deployments.

**Claim 15.**
A computer-implemented method for assembling context for a language model from a conversational knowledge graph given a query string and a token budget, the method comprising:
  encoding the query string as a dense vector using a sentence transformer model;
  retrieving the k nearest nodes from a vector index of the knowledge graph, where k defaults to 8, producing a ranked list of node identifiers and their cosine similarity scores;
  retrieving all Task nodes whose status field equals `open`;
  retrieving the most recent N `Turn` nodes, where N defaults to 5;
  iterating over nodes in priority order (recent turns, open tasks, semantic matches, user profile nodes), appending each node's text to an output context string, and stopping when the cumulative token count of the output string would exceed the provided token budget;
  formatting the output context string as a Markdown document with section headers indicating the source category and relevance score of each component;
  returning the formatted context string for injection into a language model prompt.

**Claim 16.**
The method of claim 15, wherein the token budget is typically the downstream language model's available context window minus a safety margin reserved for the model's response.

**Claim 17.**
The method of claim 15, wherein the context assembly operation ensures that recent Turn nodes are always included verbatim and in temporal order, preventing diffusion rot.

**Claim 18.**
The method of claim 15, wherein the context assembly operation ensures that all open Task nodes are included, preventing loss of commitments and pending actions.

**Claim 19.**
A computer-implemented system for maintaining a persistent user profile as a knowledge graph, the system comprising:
  storing a separate graph, co-located with but independent from conversational knowledge graphs, comprising node kinds `Preference`, `Style`, `Interest`, `Expertise`, and `Commitment`, each representing a characteristic or preference of a user;
  persisting this UserProfile graph in user-scoped storage (`~/.kgrag/profiles/<user_id>/`) rather than repo-scoped storage, ensuring that one canonical profile exists regardless of which repository or project the user is working in;
  never subjecting UserProfile nodes to pruning or removal, only to creation and update;
  providing an onboarding process that populates the UserProfile with initial values through a structured interview;
  providing an implicit learning mechanism that, when a conversation turn expresses a user preference or correction or provides personal context, updates or creates corresponding UserProfile nodes and adds edge of relation type `UPDATED_BY` from the turn to the modified profile node;
  syncing selected UserProfile fields (expertise, interests, commitments) to a PersonCorpusEntry in the KGRAG registry, making the profile visible to all KGRAG tools.

**Claim 20.**
The system of claim 19, wherein the implicit learning mechanism triggers when:
  a turn contains first-person statements of preference ("I prefer", "I like", "I want");
  a turn contains corrective statements ("stop doing X", "I don't want");
  a turn expresses learning or growth ("I'm learning about", "I'm exploring");
  a turn explicitly states a commitment ("I always", "I never").

**Claim 21.**
The system of claim 19, wherein UserProfile nodes include a field `learned_implicitly` set to True when populated through implicit learning and False when populated through explicit onboarding, enabling the system to distinguish between explicitly stated and inferred preferences.

**Claim 22.**
A computer-implemented method for implementing an agent onboarding process that populates a UserProfile graph, the method comprising:
  presenting a structured interview comprising four phases:
    Phase 1 (Identity): "What's your name and primary role?", "What projects are you mainly working in?"
    Phase 2 (Style): "Preferred language and style conventions?", "Docstring format?", "Desired verbosity level?", "Standing rules?"
    Phase 3 (Expertise): "Strongest technical domains?", "What are you learning?"
    Phase 4 (Personal): "Hobbies or interests?", "Anything that helps us work better together?";
  parsing each user response using natural language processing;
  extracting typed information (Preference, Style, Expertise, Interest, Commitment) from each response;
  creating corresponding UserProfile nodes;
  storing the complete UserProfile graph in user-scoped persistent storage;
  enabling the user to re-run the onboarding process at any time to refine or update their profile.

**Claim 23.**
A non-transitory computer-readable medium storing instructions that, when executed by one or more processors, implement a system comprising:
  a conversational graph module that maintains a directed graph of `Turn`, `Topic`, `Intent`, `Entity`, `Task`, and `Summary` nodes;
  an incremental ingestion module that executes on every incoming message, updating the graph in time independent of graph size;
  a semantic compression module implementing the KG Context Pruning algorithm;
  a context assembly module that retrieves and orders context given a query and token budget;
  a vector database interface that stores and retrieves dense vector embeddings of nodes;
  a UserProfile graph module that maintains a separate, persistent graph of user characteristics;
  a query interface exposing methods `list_topics()`, `list_tasks()`, and `assemble_context()` enabling agent self-introspection;
  an MCP server module exposing the above as callable tools for AI agent clients.

**Claim 24.**
The non-transitory computer-readable medium of claim 23, wherein the conversational graph and UserProfile graph are stored in separate SQLite databases located in repo-scoped (`.agentkg/`) and user-scoped (`~/.kgrag/profiles/`) persistent storage respectively.

**Claim 25.**
A computer-implemented method for federated querying spanning conversational memory, code knowledge, documentation, and other domain-specific knowledge graphs through a uniform interface, the method comprising:
  registering a conversational knowledge graph instance as a knowledge graph of kind `agent` in a federated knowledge graph registry;
  implementing a uniform adapter interface enabling the conversational graph to participate in federated queries alongside code graphs, documentation graphs, and other domain-specific graphs;
  upon receiving a federated query, dispatching the query to the conversational knowledge graph adapter along with adapters for other registered knowledge graphs;
  collecting and globally ranking results from all available adapters by relevance score;
  returning the globally ranked result list with per-result provenance indicating the source knowledge graph instance and domain kind;
  whereby a single query can find relevant context from conversational history, code, documentation, and other knowledge simultaneously.

---

## ABSTRACT OF THE DISCLOSURE

A conversational knowledge graph system termed AgentKG maintains an agent's memory as a live, queryable directed graph of conversation turns, topics, intents, entities, tasks, and their semantic and temporal relationships. An incremental ingestion pipeline updates the graph on every message turn using lightweight NLP (named entity recognition, intent classification) without generative language model participation. When the graph grows large, a KG Context Pruning algorithm compresses old subgraphs by clustering turns by topic proximity, summarizing each cluster via language model, creating Summary nodes, and rewiring edges—preserving semantic coherence while eliminating information loss. A dynamic context assembly mechanism retrieves context semantically rather than positionally, combining semantic retrieval, temporal recency preservation, and open-task preservation to defeat both truncation and diffusion rot. A persistent UserProfile graph stores the user's preferences, expertise, interests, and commitments, never pruned, updated both explicitly through onboarding and implicitly through conversation. The system is independently queryable—enabling the agent to introspect its own memory—and integrates with federated knowledge graph systems to enable unified queries spanning conversational memory, code, documentation, and domain-specific knowledge. The architecture treats agent cognition as a first-class knowledge graph primitive symmetric with graphs used to represent code, documents, and lived experience.
