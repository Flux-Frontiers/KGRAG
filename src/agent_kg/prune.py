"""prune.py — KG Context Pruning: the core innovation of AgentKG.

When a conversation grows long, pruning compresses old Turn subgraphs
into dense Summary nodes while preserving semantic coherence.

Algorithm:
  1. Identify the "cold subgraph" — turns older than WINDOW from current
  2. Cluster cold turns by topic proximity (cosine similarity, threshold=0.25)
  3. For each cluster of ≥ MIN_CLUSTER_SIZE turns:
     a. Collect the turn texts
     b. Summarize via LLM (Summarizer)
     c. Create a Summary node
     d. Add COMPRESSED_INTO edges (Turn → Summary)
     e. Add EXPANDS edges (Summary → Topic/Entity nodes from cluster)
  4. Delete original Turn + Intent nodes for the pruned cluster
  5. Increment pruning_pass counter

Properties of pruned graphs:
  - Lossless semantics: LLM summary captures all decisions + open questions
  - Traversable: EXPANDS edges show what topics/entities a summary covers
  - Composable: summaries themselves can be pruned in a second pass
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from agent_kg.schema import Edge, EdgeRelation, Node, NodeKind, PruneReport

if TYPE_CHECKING:
    from agent_kg.session import Session
    from agent_kg.store import AgentKGStore
    from agent_kg.summarize import Summarizer

# Pruning configuration
_DEFAULT_WINDOW = 20       # turns within this distance of current are "hot"
_MIN_CLUSTER_SIZE = 3      # minimum turns to form a prunable cluster
_TOPIC_SIM_THRESHOLD = 0.25  # cosine distance threshold for topic clustering


def _get_topic_nodes_for_turns(
    turn_ids: list[str], store: "AgentKGStore"
) -> list[Node]:
    """Return Topic nodes linked to any of the given turns via ADDRESSES edges."""
    topics: list[Node] = []
    seen_ids: set[str] = set()
    for tid in turn_ids:
        for edge in store.get_edges(source_id=tid, relation=str(EdgeRelation.ADDRESSES)):
            node = store.get_node(edge.target_id)
            if node and node.kind == NodeKind.TOPIC and node.id not in seen_ids:
                topics.append(node)
                seen_ids.add(node.id)
    return topics


def _get_entity_nodes_for_turns(
    turn_ids: list[str], store: "AgentKGStore"
) -> list[Node]:
    """Return Entity nodes linked to any of the given turns via MENTIONS edges."""
    entities: list[Node] = []
    seen_ids: set[str] = set()
    for tid in turn_ids:
        for edge in store.get_edges(source_id=tid, relation=str(EdgeRelation.MENTIONS)):
            node = store.get_node(edge.target_id)
            if node and node.kind == NodeKind.ENTITY and node.id not in seen_ids:
                entities.append(node)
                seen_ids.add(node.id)
    return entities


def _cluster_turns_by_topic(
    turns: list[Node],
    store: "AgentKGStore",
    threshold: float = _TOPIC_SIM_THRESHOLD,
) -> list[list[Node]]:
    """Cluster turns by topic proximity using cosine distance over embeddings.

    Uses a greedy single-linkage approach: start a new cluster when no
    existing cluster is within ``threshold`` cosine distance.

    Falls back to a single sequential cluster if embeddings are unavailable.
    """
    if not turns:
        return []

    # Try embedding-based clustering
    try:
        turn_vecs: list[list[float]] = []
        for t in turns:
            vec = store.embed(t.text or t.label or "")
            turn_vecs.append(vec)

        def _cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            return dot  # already normalized (SentenceTransformer)

        clusters: list[list[int]] = []  # list of turn indices per cluster
        for i, vec in enumerate(turn_vecs):
            placed = False
            for cluster in clusters:
                # Compare to centroid of cluster (mean of vectors)
                centroid = [
                    sum(turn_vecs[j][d] for j in cluster) / len(cluster)
                    for d in range(len(vec))
                ]
                sim = _cosine_sim(vec, centroid)
                if sim >= (1.0 - threshold):
                    cluster.append(i)
                    placed = True
                    break
            if not placed:
                clusters.append([i])

        return [[turns[i] for i in cluster] for cluster in clusters]

    except Exception:  # pylint: disable=broad-exception-caught
        # Fallback: sequential windows of MIN_CLUSTER_SIZE
        result = []
        for i in range(0, len(turns), _MIN_CLUSTER_SIZE):
            result.append(turns[i: i + _MIN_CLUSTER_SIZE])
        return result


def prune(
    store: "AgentKGStore",
    summarizer: "Summarizer",
    session: "Session | None" = None,
    window: int = _DEFAULT_WINDOW,
    token_budget: int | None = None,
) -> PruneReport:
    """Execute one KG Context Pruning pass.

    :param store: The backing store.
    :param summarizer: LLM backend for cluster summarization.
    :param session: Active session (used for pruning_pass tracking).
    :param window: Number of most-recent turns to keep verbatim (not pruned).
    :param token_budget: If given, prune until total turn tokens ≤ budget.
    :return: :class:`~agent_kg.schema.PruneReport` with pass statistics.
    """
    now = datetime.now(UTC)

    # Get all turns ordered by turn_index
    all_turns = store.get_all_turns()
    if len(all_turns) <= window:
        return PruneReport(
            summaries_created=0,
            turns_pruned=0,
            nodes_removed=0,
            pruning_pass=0,
        )

    # Identify cold turns (older than window)
    cold_turns = sorted(all_turns, key=lambda t: t.turn_index)[:-window]
    if len(cold_turns) < _MIN_CLUSTER_SIZE:
        return PruneReport(
            summaries_created=0,
            turns_pruned=0,
            nodes_removed=0,
            pruning_pass=0,
        )

    # Determine current pruning_pass from an existing node (or 0)
    current_pruning_pass = max((t.pruning_pass for t in all_turns), default=0)
    new_pruning_pass = current_pruning_pass + 1

    # Cluster cold turns by topic proximity
    clusters = _cluster_turns_by_topic(cold_turns, store)
    pruneable = [c for c in clusters if len(c) >= _MIN_CLUSTER_SIZE]

    summaries_created = 0
    turns_pruned = 0
    nodes_removed = 0
    token_savings = 0

    for cluster in pruneable:
        turn_ids = [t.id for t in cluster]

        # Collect cluster text
        cluster_text = "\n\n".join(
            f"[{t.role.upper() if t.role else 'TURN'}] {t.text}" for t in cluster
        )
        token_savings += sum(t.token_count for t in cluster)

        # Summarize via LLM
        summary_text = summarizer.summarize(cluster_text)
        if not summary_text:
            continue  # skip cluster if summarization failed

        # Get linked topics + entities for EXPANDS edges
        topic_nodes = _get_topic_nodes_for_turns(turn_ids, store)
        entity_nodes = _get_entity_nodes_for_turns(turn_ids, store)

        # Create Summary node
        summary_node = Node(
            kind=NodeKind.SUMMARY,
            label=summary_text[:80],
            text=summary_text,
            covers_turns=turn_ids,
            pruning_pass=new_pruning_pass,
            session_id=cluster[0].session_id,
            created_at=now,
            updated_at=now,
            first_seen=cluster[0].first_seen,
            last_seen=cluster[-1].last_seen,
        )
        store.upsert_node(summary_node)
        try:
            store.embed_node(summary_node)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        # COMPRESSED_INTO edges: each pruned turn → summary
        for turn in cluster:
            store.add_edge(
                Edge(
                    source_id=turn.id,
                    target_id=summary_node.id,
                    relation=EdgeRelation.COMPRESSED_INTO,
                )
            )

        # EXPANDS edges: summary → each topic + entity it covers
        for topic in topic_nodes:
            store.add_edge(
                Edge(source_id=summary_node.id, target_id=topic.id, relation=EdgeRelation.EXPANDS)
            )
        for entity in entity_nodes:
            store.add_edge(
                Edge(source_id=summary_node.id, target_id=entity.id, relation=EdgeRelation.EXPANDS)
            )

        # Delete original Turn nodes (CASCADE removes their edges except COMPRESSED_INTO/EXPANDS)
        # Note: we delete Intent nodes too since they're turn-specific
        intent_ids = []
        for tid in turn_ids:
            for edge in store.get_edges(source_id=tid, relation=str(EdgeRelation.EXPRESSES)):
                intent_ids.append(edge.target_id)

        store.delete_nodes(turn_ids)
        if intent_ids:
            store.delete_nodes(intent_ids)

        summaries_created += 1
        turns_pruned += len(cluster)
        nodes_removed += len(cluster) + len(intent_ids)

    # Update session pruning pass counter
    if session and summaries_created > 0:
        session.record_prune()

    return PruneReport(
        summaries_created=summaries_created,
        turns_pruned=turns_pruned,
        nodes_removed=nodes_removed,
        pruning_pass=new_pruning_pass if summaries_created > 0 else current_pruning_pass,
        token_savings_approx=token_savings,
    )


def should_prune(
    store: "AgentKGStore",
    window: int = _DEFAULT_WINDOW,
    token_budget: int | None = None,
) -> bool:
    """Return True if a pruning pass is warranted.

    :param store: The backing store.
    :param window: Hot window size.
    :param token_budget: Optional token budget trigger.
    :return: True if the cold subgraph is large enough to prune.
    """
    all_turns = store.get_all_turns()
    cold_count = max(0, len(all_turns) - window)
    if cold_count >= _MIN_CLUSTER_SIZE * 2:
        return True
    if token_budget is not None:
        total_tokens = sum(t.token_count for t in all_turns)
        if total_tokens > token_budget * 0.6:
            return True
    return False
