#!/usr/bin/env python3
"""
TextKG Analysis — Comprehensive Analytics for doc_kg and diary_kg

Generates detailed analysis reports of the DocKG / DiaryKG SQLite graph:
entity mentions, topic coverage, edge relationship patterns, temporal
clustering (diary), co-occurrence networks, hot chunks, and semantic
coverage quality metrics.

Usage
-----
  # Auto-detect DiaryKG root (reads .diarykg/graph.sqlite + corpus/*.md)
  python textkg_analysis.py --root /path/to/project

  # Point directly at a SQLite database
  python textkg_analysis.py --db /path/to/graph.sqlite

  # With a corpus dir for temporal / frontmatter enrichment
  python textkg_analysis.py --db /path/to/graph.sqlite --corpus /path/to/corpus

  # Save markdown report
  python textkg_analysis.py --root . --output analysis_report.md

Features
--------
- Node kind distribution (document, section, chunk, topic, entity, keyword)
- Edge relation distribution with histogram
- Top entities by mention count and co-occurrence network
- Topic and keyword frequency tables
- Hot chunks (highest connectivity)
- Semantic extraction coverage ratios
- Temporal distribution from diary frontmatter timestamps
- Comparative density statistics
- Full Markdown report generation
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ---------------------------------------------------------------------------
# Frontmatter parser (mirrors DiaryKG._parse_frontmatter)
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> Dict[str, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}
    result: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ": " in line:
            k, _, v = line.partition(": ")
            result[k.strip()] = v.strip()
    return result


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

DIARY_KG_DIR = ".diarykg"


def resolve_paths(
    root: Optional[str],
    db: Optional[str],
    corpus: Optional[str],
) -> Tuple[Path, Optional[Path]]:
    """Return (db_path, corpus_dir) from CLI arguments.

    Priority:
    1. Explicit --db overrides everything.
    2. --root auto-discovers .diarykg/graph.sqlite and .diarykg/corpus/.
    3. --corpus adds optional frontmatter enrichment when --db is given.
    """
    if db:
        db_path = Path(db).resolve()
        corpus_dir = Path(corpus).resolve() if corpus else None
        return db_path, corpus_dir

    if root:
        root_path = Path(root).resolve()
        db_path = root_path / DIARY_KG_DIR / "graph.sqlite"
        corpus_dir = root_path / DIARY_KG_DIR / "corpus"
        if not db_path.exists():
            # Fall back: maybe it's a raw doc_kg project
            alt = root_path / "graph.sqlite"
            if alt.exists():
                db_path = alt
                corpus_dir = root_path / "corpus" if (root_path / "corpus").exists() else None
        return db_path, corpus_dir if (corpus_dir and corpus_dir.exists()) else None

    console.print("[red]Error:[/red] Provide --root or --db.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# SQLite data collection
# ---------------------------------------------------------------------------


def collect_graph_data(db_path: Path) -> Dict[str, Any]:
    """Query the SQLite database and collect all analytics data."""
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found: {db_path}")
        sys.exit(1)

    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    data: Dict[str, Any] = {"db_path": str(db_path)}

    # ---- baseline counts ----
    node_rows = con.execute("SELECT kind, COUNT(*) AS cnt FROM nodes GROUP BY kind").fetchall()
    edge_rows = con.execute("SELECT rel,  COUNT(*) AS cnt FROM edges GROUP BY rel").fetchall()
    data["node_counts"] = {r["kind"]: r["cnt"] for r in node_rows}
    data["edge_counts"] = {r["rel"]:  r["cnt"] for r in edge_rows}
    data["total_nodes"] = sum(data["node_counts"].values())
    data["total_edges"] = sum(data["edge_counts"].values())

    # ---- top entities by MENTIONS_ENTITY in-degree ----
    entity_rows = con.execute(
        """
        SELECT n.name, n.title, COUNT(e.src) AS mentions
        FROM nodes n
        LEFT JOIN edges e ON e.dst = n.id AND e.rel = 'MENTIONS_ENTITY'
        WHERE n.kind = 'entity'
        GROUP BY n.id
        ORDER BY mentions DESC
        LIMIT 40
        """
    ).fetchall()
    data["entities"] = [dict(r) for r in entity_rows]

    # ---- top topics by HAS_TOPIC in-degree ----
    topic_rows = con.execute(
        """
        SELECT n.name, n.title, COUNT(e.src) AS mentions
        FROM nodes n
        LEFT JOIN edges e ON e.dst = n.id AND e.rel = 'HAS_TOPIC'
        WHERE n.kind = 'topic'
        GROUP BY n.id
        ORDER BY mentions DESC
        LIMIT 30
        """
    ).fetchall()
    data["topics"] = [dict(r) for r in topic_rows]

    # ---- top keywords by HAS_KEYWORD in-degree ----
    kw_rows = con.execute(
        """
        SELECT n.name, n.title, COUNT(e.src) AS mentions
        FROM nodes n
        LEFT JOIN edges e ON e.dst = n.id AND e.rel = 'HAS_KEYWORD'
        WHERE n.kind = 'keyword'
        GROUP BY n.id
        ORDER BY mentions DESC
        LIMIT 30
        """
    ).fetchall()
    data["keywords"] = [dict(r) for r in kw_rows]

    # ---- entity co-occurrences (CO_OCCURS_WITH between entity nodes) ----
    cooccur_rows = con.execute(
        """
        SELECT a.name AS entity1, b.name AS entity2, COUNT(*) AS cnt
        FROM edges e
        JOIN nodes a ON a.id = e.src AND a.kind = 'entity'
        JOIN nodes b ON b.id = e.dst AND b.kind = 'entity'
        WHERE e.rel = 'CO_OCCURS_WITH'
        GROUP BY e.src, e.dst
        ORDER BY cnt DESC
        LIMIT 25
        """
    ).fetchall()
    data["cooccurrences"] = [dict(r) for r in cooccur_rows]

    # ---- hot chunks: most outgoing semantic links ----
    hot_rows = con.execute(
        """
        SELECT
          n.id,
          COALESCE(n.title, n.name, n.id) AS label,
          n.file_path,
          SUM(CASE WHEN e.rel IN ('HAS_TOPIC','MENTIONS_ENTITY','HAS_KEYWORD','CO_OCCURS_WITH','SIMILAR_TO')
                   THEN 1 ELSE 0 END) AS semantic_links,
          SUM(CASE WHEN e.rel = 'REFERENCES' THEN 1 ELSE 0 END) AS refs,
          COUNT(*) AS total_links
        FROM nodes n
        JOIN edges e ON e.src = n.id
        WHERE n.kind = 'chunk'
        GROUP BY n.id
        ORDER BY semantic_links DESC, total_links DESC
        LIMIT 15
        """
    ).fetchall()
    data["hot_chunks"] = [dict(r) for r in hot_rows]

    # ---- per-document chunk / section counts ----
    doc_rows = con.execute(
        """
        SELECT
          n.file_path,
          SUM(CASE WHEN n.kind = 'chunk'   THEN 1 ELSE 0 END) AS chunks,
          SUM(CASE WHEN n.kind = 'section' THEN 1 ELSE 0 END) AS sections
        FROM nodes n
        WHERE n.file_path IS NOT NULL
        GROUP BY n.file_path
        ORDER BY chunks DESC
        LIMIT 20
        """
    ).fetchall()
    data["document_metrics"] = [dict(r) for r in doc_rows]

    # ---- semantic coverage ----
    chunk_count = data["node_counts"].get("chunk", 0)
    if chunk_count:
        def _covered(rel: str) -> int:
            return con.execute(
                "SELECT COUNT(DISTINCT src) FROM edges WHERE rel = ?", (rel,)
            ).fetchone()[0]

        data["semantic_coverage"] = {
            "topic":   _covered("HAS_TOPIC")        / chunk_count,
            "entity":  _covered("MENTIONS_ENTITY")   / chunk_count,
            "keyword": _covered("HAS_KEYWORD")       / chunk_count,
            "similar": _covered("SIMILAR_TO")        / chunk_count,
        }
    else:
        data["semantic_coverage"] = {
            "topic": 0.0, "entity": 0.0, "keyword": 0.0, "similar": 0.0
        }

    con.close()
    return data


# ---------------------------------------------------------------------------
# Corpus frontmatter scan (diary enrichment)
# ---------------------------------------------------------------------------


def collect_corpus_data(corpus_dir: Path) -> Dict[str, Any]:
    """Scan corpus .md files for temporal and category data."""
    md_files = list(corpus_dir.rglob("*.md"))
    timestamps: List[str] = []
    categories: Counter = Counter()
    contexts: Counter = Counter()
    entry_indices: set = set()

    for md in md_files:
        try:
            fm = _parse_frontmatter(md.read_text(encoding="utf-8"))
        except OSError:
            continue
        if fm.get("timestamp"):
            timestamps.append(fm["timestamp"])
        if fm.get("category"):
            categories[fm["category"]] += 1
        if fm.get("context"):
            contexts[fm["context"]] += 1
        if fm.get("entry_index"):
            entry_indices.add(fm["entry_index"])

    timestamps.sort()

    # Temporal distribution: count by year-month
    monthly: Counter = Counter()
    for ts in timestamps:
        ym = ts[:7]  # "YYYY-MM"
        if ym:
            monthly[ym] += 1

    return {
        "chunk_files": len(md_files),
        "entry_count": len(entry_indices),
        "timestamps": timestamps,
        "temporal_distribution": dict(sorted(monthly.items())),
        "category_counts": dict(categories.most_common()),
        "context_counts": dict(contexts.most_common()),
    }


# ---------------------------------------------------------------------------
# Rich display helpers
# ---------------------------------------------------------------------------


def _bar(value: int, max_value: int, width: int = 30) -> str:
    if max_value == 0:
        return ""
    return "█" * max(1, int(value / max_value * width))


def display_summary_panel(graph: Dict[str, Any], corpus: Optional[Dict[str, Any]], db_path: Path) -> None:
    nc = graph["node_counts"]
    ec = graph["edge_counts"]
    content = Text()

    content.append("Database:  ", style="bold cyan")
    content.append(f"{db_path}\n", style="white")
    content.append("\n")

    content.append("Nodes:     ", style="bold cyan")
    content.append(f"{graph['total_nodes']:,}", style="bold white")
    content.append("  (documents: ")
    content.append(str(nc.get("document", 0)), style="green")
    content.append("  sections: ")
    content.append(str(nc.get("section", 0)), style="green")
    content.append("  chunks: ")
    content.append(str(nc.get("chunk", 0)), style="green")
    content.append(")\n")

    content.append("Semantic:  ", style="bold cyan")
    content.append(f"entities={nc.get('entity',0):,}  topics={nc.get('topic',0):,}  keywords={nc.get('keyword',0):,}\n", style="white")

    content.append("Edges:     ", style="bold cyan")
    content.append(f"{graph['total_edges']:,}\n", style="bold white")

    chunk_count = nc.get("chunk", 0)
    if chunk_count:
        edges_per_chunk = graph["total_edges"] / chunk_count
        content.append("\nEdges/chunk:  ", style="bold yellow")
        content.append(f"{edges_per_chunk:.1f}\n", style="white")

    if corpus:
        content.append("\n")
        content.append("Corpus files: ", style="bold cyan")
        content.append(f"{corpus['chunk_files']}  (entries: {corpus['entry_count']})\n", style="white")
        if corpus["timestamps"]:
            ts = corpus["timestamps"]
            content.append("Time span:    ", style="bold cyan")
            content.append(f"{ts[0][:10]}  →  {ts[-1][:10]}\n", style="white")

    sc = graph["semantic_coverage"]
    content.append("\nSemantic coverage:  ", style="bold yellow")
    content.append(
        f"topics={sc['topic']:.0%}  entities={sc['entity']:.0%}"
        f"  keywords={sc['keyword']:.0%}  similar={sc['similar']:.0%}\n",
        style="white",
    )

    console.print(Panel(content, title="TextKG Analysis", border_style="cyan", box=box.DOUBLE))


def display_node_kinds_table(graph: Dict[str, Any]) -> None:
    table = Table(title="Node Kind Distribution", box=box.ROUNDED)
    table.add_column("Kind", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Share", style="green", justify="right")
    table.add_column("Visualization", style="blue")

    total = graph["total_nodes"]
    max_cnt = max(graph["node_counts"].values(), default=1)
    for kind, cnt in sorted(graph["node_counts"].items(), key=lambda x: x[1], reverse=True):
        pct = cnt / total * 100 if total else 0
        table.add_row(kind, f"{cnt:,}", f"{pct:.1f}%", _bar(cnt, max_cnt))
    console.print(table)


def display_edge_rels_table(graph: Dict[str, Any]) -> None:
    table = Table(title="Edge Relation Distribution", box=box.ROUNDED)
    table.add_column("Relation", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Share", style="green", justify="right")
    table.add_column("Visualization", style="blue")

    total = graph["total_edges"]
    max_cnt = max(graph["edge_counts"].values(), default=1)
    for rel, cnt in sorted(graph["edge_counts"].items(), key=lambda x: x[1], reverse=True):
        pct = cnt / total * 100 if total else 0
        table.add_row(rel, f"{cnt:,}", f"{pct:.1f}%", _bar(cnt, max_cnt))
    console.print(table)


def display_entities_table(graph: Dict[str, Any], limit: int = 30) -> None:
    entities = graph["entities"][:limit]
    if not entities:
        return

    table = Table(title=f"Top {limit} Entities by Mention Count", box=box.ROUNDED)
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Entity", style="cyan")
    table.add_column("Mentions", style="magenta", justify="right")
    table.add_column("Activity", style="blue")

    max_m = entities[0]["mentions"] if entities else 1
    for i, ent in enumerate(entities, 1):
        label = ent.get("title") or ent["name"]
        table.add_row(f"#{i}", label[:45], f"{ent['mentions']:,}", _bar(ent["mentions"], max_m))
    console.print(table)


def display_topics_table(graph: Dict[str, Any]) -> None:
    topics = graph["topics"]
    if not topics:
        return

    table = Table(title="Top Topics by Chunk Coverage", box=box.ROUNDED)
    table.add_column("Topic", style="cyan")
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Visualization", style="blue")

    max_m = topics[0]["mentions"] if topics else 1
    for t in topics:
        label = t.get("title") or t["name"]
        table.add_row(label[:45], f"{t['mentions']:,}", _bar(t["mentions"], max_m))
    console.print(table)


def display_keywords_table(graph: Dict[str, Any]) -> None:
    keywords = graph["keywords"]
    if not keywords:
        return

    table = Table(title="Top Keywords by Chunk Coverage", box=box.ROUNDED)
    table.add_column("Keyword", style="cyan")
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Visualization", style="blue")

    max_m = keywords[0]["mentions"] if keywords else 1
    for kw in keywords[:20]:
        label = kw.get("title") or kw["name"]
        table.add_row(label[:45], f"{kw['mentions']:,}", _bar(kw["mentions"], max_m))
    console.print(table)


def display_cooccurrence_table(graph: Dict[str, Any]) -> None:
    cooccur = graph["cooccurrences"]
    if not cooccur:
        return

    table = Table(title="Top Entity Co-occurrences", box=box.ROUNDED)
    table.add_column("Entity 1", style="cyan")
    table.add_column("↔", style="dim", width=3)
    table.add_column("Entity 2", style="green")
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Strength", style="blue")

    max_cnt = cooccur[0]["cnt"] if cooccur else 1
    for row in cooccur:
        table.add_row(
            row["entity1"][:25], "↔", row["entity2"][:25],
            f"{row['cnt']:,}", "●" * max(1, int(row["cnt"] / max_cnt * 12)),
        )
    console.print(table)


def display_hot_chunks_table(graph: Dict[str, Any]) -> None:
    hot = graph["hot_chunks"]
    if not hot:
        return

    table = Table(title="Hot Chunks (Most Connected)", box=box.ROUNDED)
    table.add_column("Label", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Semantic", style="magenta", justify="right")
    table.add_column("Refs", style="yellow", justify="right")
    table.add_column("Total", style="green", justify="right")

    for h in hot:
        fp = (h.get("file_path") or "")
        fp_short = fp.split("/")[-1] if "/" in fp else fp
        table.add_row(
            (h["label"] or "")[:40],
            fp_short[:30],
            str(h["semantic_links"]),
            str(h["refs"]),
            str(h["total_links"]),
        )
    console.print(table)


def display_temporal_table(corpus: Dict[str, Any]) -> None:
    dist = corpus.get("temporal_distribution", {})
    if not dist:
        return

    table = Table(title="Temporal Distribution (Diary Entries by Month)", box=box.ROUNDED)
    table.add_column("Year-Month", style="cyan", width=12)
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Timeline", style="blue")

    max_cnt = max(dist.values(), default=1)
    for ym, cnt in dist.items():
        table.add_row(ym, f"{cnt:,}", _bar(cnt, max_cnt, width=40))
    console.print(table)


def display_category_table(corpus: Dict[str, Any]) -> None:
    cats = corpus.get("category_counts", {})
    if not cats:
        return

    table = Table(title="Corpus Category Distribution", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Chunks", style="magenta", justify="right")
    table.add_column("Visualization", style="blue")

    max_cnt = max(cats.values(), default=1)
    for cat, cnt in cats.items():
        table.add_row(cat[:40], f"{cnt:,}", _bar(cnt, max_cnt))
    console.print(table)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def write_markdown_report(
    graph: Dict[str, Any],
    corpus: Optional[Dict[str, Any]],
    db_path: Path,
    output_path: Path,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nc = graph["node_counts"]
    ec = graph["edge_counts"]
    sc = graph["semantic_coverage"]
    chunk_count = nc.get("chunk", 0)

    lines: List[str] = [
        "# TextKG Analysis Report",
        "",
        f"**Database**: `{db_path}`  ",
        f"**Generated**: {ts}  ",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        "|--------|-------|",
        f"| Total Nodes | {graph['total_nodes']:,} |",
        f"| Total Edges | {graph['total_edges']:,} |",
        f"| Documents   | {nc.get('document', 0):,} |",
        f"| Sections    | {nc.get('section', 0):,} |",
        f"| Chunks      | {nc.get('chunk', 0):,} |",
        f"| Entities    | {nc.get('entity', 0):,} |",
        f"| Topics      | {nc.get('topic', 0):,} |",
        f"| Keywords    | {nc.get('keyword', 0):,} |",
    ]
    if chunk_count:
        lines.append(f"| Edges/Chunk | {graph['total_edges']/chunk_count:.1f} |")
    lines.append("")

    if corpus:
        ts_list = corpus.get("timestamps", [])
        lines += [
            "## Corpus",
            "",
            f"- Chunk files   : **{corpus['chunk_files']}**",
            f"- Diary entries : **{corpus['entry_count']}**",
        ]
        if ts_list:
            lines.append(f"- Time span     : **{ts_list[0][:10]}** → **{ts_list[-1][:10]}**")
        lines.append("")

    # Semantic coverage
    lines += [
        "## Semantic Coverage",
        "",
        f"| Feature | Coverage |",
        "|---------|----------|",
        f"| Topics   | {sc['topic']:.1%} |",
        f"| Entities | {sc['entity']:.1%} |",
        f"| Keywords | {sc['keyword']:.1%} |",
        f"| Similar  | {sc['similar']:.1%} |",
        "",
    ]

    # Node kinds
    lines += ["## Node Kind Distribution", "", "| Kind | Count | Share | Bar |", "|------|------:|------:|-----|"]
    total = graph["total_nodes"]
    for kind, cnt in sorted(nc.items(), key=lambda x: x[1], reverse=True):
        pct = cnt / total * 100 if total else 0
        bar = "█" * max(1, int(pct / 2))
        lines.append(f"| {kind} | {cnt:,} | {pct:.1f}% | `{bar}` |")
    lines.append("")

    # Edge relations
    lines += ["## Edge Relation Distribution", "", "| Relation | Count | Share | Bar |", "|----------|------:|------:|-----|"]
    total_e = graph["total_edges"]
    for rel, cnt in sorted(ec.items(), key=lambda x: x[1], reverse=True):
        pct = cnt / total_e * 100 if total_e else 0
        bar = "█" * max(1, int(pct / 2))
        lines.append(f"| {rel} | {cnt:,} | {pct:.1f}% | `{bar}` |")
    lines.append("")

    # Top entities
    entities = graph["entities"]
    if entities:
        lines += [
            f"## Top {min(30, len(entities))} Entities by Mention Count",
            "",
            "| Rank | Entity | Mentions | Bar |",
            "|------|--------|--------:|-----|",
        ]
        max_m = entities[0]["mentions"] if entities else 1
        for i, ent in enumerate(entities[:30], 1):
            label = (ent.get("title") or ent["name"]).replace("|", "\\|")
            bar = "▓" * max(1, int(ent["mentions"] / max_m * 25))
            lines.append(f"| {i} | {label} | {ent['mentions']:,} | `{bar}` |")
        lines.append("")

    # Topics
    topics = graph["topics"]
    if topics:
        lines += [
            f"## Top {min(25, len(topics))} Topics",
            "",
            "| Topic | Chunks | Bar |",
            "|-------|-------:|-----|",
        ]
        max_t = topics[0]["mentions"] if topics else 1
        for t in topics[:25]:
            label = (t.get("title") or t["name"]).replace("|", "\\|")
            bar = "▓" * max(1, int(t["mentions"] / max_t * 20))
            lines.append(f"| {label} | {t['mentions']:,} | `{bar}` |")
        lines.append("")

    # Keywords
    keywords = graph["keywords"]
    if keywords:
        lines += [
            "## Top Keywords",
            "",
            "| Keyword | Chunks | Bar |",
            "|---------|-------:|-----|",
        ]
        max_k = keywords[0]["mentions"] if keywords else 1
        for kw in keywords[:20]:
            label = (kw.get("title") or kw["name"]).replace("|", "\\|")
            bar = "▓" * max(1, int(kw["mentions"] / max_k * 20))
            lines.append(f"| {label} | {kw['mentions']:,} | `{bar}` |")
        lines.append("")

    # Co-occurrences
    cooccur = graph["cooccurrences"]
    if cooccur:
        lines += [
            "## Entity Co-occurrence Network",
            "",
            "| Entity 1 | Entity 2 | Count |",
            "|----------|----------|------:|",
        ]
        for row in cooccur:
            e1 = row["entity1"].replace("|", "\\|")
            e2 = row["entity2"].replace("|", "\\|")
            lines.append(f"| {e1} | {e2} | {row['cnt']:,} |")
        lines.append("")

    # Hot chunks
    hot = graph["hot_chunks"]
    if hot:
        lines += [
            "## Hot Chunks",
            "",
            "| Label | File | Semantic Links | Refs | Total |",
            "|-------|------|---:|---:|---:|",
        ]
        for h in hot:
            fp = (h.get("file_path") or "").split("/")[-1]
            label = (h["label"] or "").replace("|", "\\|")[:50]
            lines.append(
                f"| {label} | `{fp}` | {h['semantic_links']} | {h['refs']} | {h['total_links']} |"
            )
        lines.append("")

    # Temporal distribution (diary)
    if corpus:
        dist = corpus.get("temporal_distribution", {})
        if dist:
            max_cnt = max(dist.values(), default=1)
            lines += [
                "## Temporal Distribution",
                "",
                "Memory creation timeline by month:",
                "",
                "```",
            ]
            for ym, cnt in dist.items():
                bar = "█" * max(1, int(cnt / max_cnt * 50))
                lines.append(f"{ym}  {bar} {cnt:3d}")
            lines += ["```", ""]

        cats = corpus.get("category_counts", {})
        if cats:
            lines += [
                "## Category Distribution",
                "",
                "| Category | Chunks |",
                "|----------|-------:|",
            ]
            for cat, cnt in cats.items():
                lines.append(f"| {cat} | {cnt} |")
            lines.append("")

        ctxs = corpus.get("context_counts", {})
        if ctxs:
            lines += [
                "## Context Distribution",
                "",
                "| Context | Chunks |",
                "|---------|-------:|",
            ]
            for ctx, cnt in ctxs.items():
                lines.append(f"| {ctx} | {cnt} |")
            lines.append("")

    # Insights
    lines += ["## Insights", ""]
    insights: List[str] = []

    if chunk_count:
        epk = graph["total_edges"] / chunk_count
        if epk > 8:
            insights.append(f"Strong connectivity: {epk:.1f} edges/chunk — rich semantic graph.")
        elif epk > 4:
            insights.append(f"Good connectivity: {epk:.1f} edges/chunk.")
        else:
            insights.append(f"Low connectivity ({epk:.1f} edges/chunk); consider enabling more extraction features.")

    for feat, label in [("topic", "topic"), ("entity", "entity"), ("keyword", "keyword")]:
        cov = sc.get(feat, 0.0)
        if cov >= 0.6:
            insights.append(f"Strong {label} coverage ({cov:.0%}) across chunks.")
        elif cov < 0.25:
            insights.append(f"Low {label} coverage ({cov:.0%}); consider tuning extraction thresholds.")

    if entities:
        top10_sum = sum(e["mentions"] for e in entities[:10])
        all_sum = sum(e["mentions"] for e in graph["entities"])
        if all_sum:
            conc = top10_sum / all_sum
            insights.append(
                f"Top-10 entities account for {conc:.0%} of all mentions "
                f"({'centralised' if conc > 0.5 else 'distributed'} graph)."
            )

    if corpus and corpus.get("temporal_distribution"):
        n_months = len(corpus["temporal_distribution"])
        if n_months > 12:
            insights.append(f"Excellent longitudinal coverage: {n_months} months of diary data.")
        else:
            insights.append(f"Temporal coverage: {n_months} months.")

    for insight in insights:
        lines.append(f"- {insight}")
    lines += ["", "---", "", "*Report generated by TextKG Analysis*", ""]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]✓ Markdown report saved:[/green] {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse a doc_kg or diary_kg SQLite knowledge graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--root", "-r",
        default=None,
        help="DiaryKG project root (auto-discovers .diarykg/graph.sqlite and corpus/).",
    )
    parser.add_argument(
        "--db", "-d",
        default=None,
        help="Direct path to graph.sqlite (overrides --root).",
    )
    parser.add_argument(
        "--corpus", "-c",
        default=None,
        help="Path to corpus directory containing .md chunk files (for temporal/category data).",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        type=Path,
        help="Write Markdown report to this file.",
    )
    parser.add_argument(
        "--no-console",
        action="store_true",
        help="Skip rich console tables; only write the Markdown report.",
    )
    args = parser.parse_args()

    # Resolve paths
    if not args.root and not args.db:
        args.root = "."

    db_path, corpus_dir = resolve_paths(args.root, args.db, args.corpus)

    # Collect data
    with console.status("[bold cyan]Querying graph database..."):
        graph_data = collect_graph_data(db_path)

    corpus_data: Optional[Dict[str, Any]] = None
    if corpus_dir and corpus_dir.exists():
        with console.status("[bold cyan]Scanning corpus frontmatter..."):
            corpus_data = collect_corpus_data(corpus_dir)

    # Display
    if not args.no_console:
        console.print()
        display_summary_panel(graph_data, corpus_data, db_path)
        console.print()
        display_node_kinds_table(graph_data)
        console.print()
        display_edge_rels_table(graph_data)
        if graph_data["entities"]:
            console.print()
            display_entities_table(graph_data, limit=25)
        if graph_data["topics"]:
            console.print()
            display_topics_table(graph_data)
        if graph_data["keywords"]:
            console.print()
            display_keywords_table(graph_data)
        if graph_data["cooccurrences"]:
            console.print()
            display_cooccurrence_table(graph_data)
        if graph_data["hot_chunks"]:
            console.print()
            display_hot_chunks_table(graph_data)
        if corpus_data:
            if corpus_data.get("temporal_distribution"):
                console.print()
                display_temporal_table(corpus_data)
            if corpus_data.get("category_counts"):
                console.print()
                display_category_table(corpus_data)

    # Markdown report
    if args.output:
        output_file = args.output
    else:
        slug = db_path.parent.name
        output_file = Path.cwd() / f"textkg_report_{slug}_{datetime.now().strftime('%Y%m%d')}.md"

    console.print()
    write_markdown_report(graph_data, corpus_data, db_path, output_file)

    console.print()
    console.print("[bold green]Analysis complete.[/bold green]")
    console.print(f"  Nodes : [magenta]{graph_data['total_nodes']:,}[/magenta]")
    console.print(f"  Edges : [magenta]{graph_data['total_edges']:,}[/magenta]")
    console.print(f"  Report: [cyan]{output_file}[/cyan]")


if __name__ == "__main__":
    main()
