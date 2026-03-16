# Semantic Chunking Strategy

This document describes how KGRAG ingests raw text into the knowledge graph —
specifically how diary entries (and by extension, any prose corpus) are split
into indexable units and what metadata travels with each unit.

---

## Overview

Chunking sits at the boundary between raw text and the graph.  Its job is to
cut a continuous stream of prose into self-contained pieces that are small
enough to be useful as retrieval units yet large enough to carry meaningful
context.  Every chunk becomes a node in the DocKG SQLite graph and a vector in
the LanceDB semantic index.

Three strategies are available.  **`sentence_group`** is the recommended
default for most corpora; `semantic` is best when topic boundaries are
important; `hybrid` bridges the two.

---

## Pipeline

```
Raw diary file (.txt)
        │
        ▼
DiaryTransformer.ingest_to_corpus()
   ├─ Parse entries (DiaryParser)
   ├─ Classify entries (DiaryClassifier)
   │     ├─ semantic_category  (TF-IDF k-means or supervised)
   │     └─ context_classification  (rule-based NLP)
   └─ Segment content (segment_content())
         ├─ Strip temporal preamble
         ├─ Tokenise sentences  [spaCy en_core_web_sm]
         └─ Apply chosen chunking strategy
                 │
                 ▼
        .md chunk files  (.diarykg/corpus/)
                │
                ▼
        DocKG.build()
   ├─ SQLite graph  (.diarykg/graph.sqlite)
   └─ LanceDB vectors  (.diarykg/lancedb/)
```

---

## Chunking Strategies

### `sentence_group`  *(default)*

Groups exactly **N consecutive sentences** into one chunk, then starts a new
group.  Fast, predictable, and consistent across corpora of any size.

```
sentences: [S1, S2, S3, S4, S5, S6, S7]   (N=4)
chunks:    [S1 S2 S3 S4]  [S5 S6 S7]
```

Best for: diary corpora, informal prose, large batches where speed matters.

### `semantic`

Encodes every sentence with a `sentence-transformers` model
(`all-MiniLM-L6-v2`) and computes the cosine similarity between each adjacent
pair.  A **dynamic threshold** is then derived:

```
threshold = mean(similarities) − std(similarities)
```

A chunk boundary is inserted wherever the similarity drops below the threshold,
indicating a topic shift.  Chunks vary in length because they track the natural
rhythm of the text rather than a fixed sentence count.

```
sentences: [S1, S2,  S3, S4, S5,  S6, S7]
sims:           0.91  0.87 0.42 0.88  0.89
                             ↑
                         boundary (below threshold)
chunks:    [S1 S2 S3 S4]   [S5 S6 S7]
```

Chunks that still exceed `max_chunk_length` are further split at word
boundaries (`_split_by_length`).

Best for: long-form documents with clear thematic shifts, analytical queries.

### `hybrid`

Groups sentences in batches of **N** (like `sentence_group`) but imposes a
hard **character cap** per chunk.  If adding the next sentence would exceed the
cap, the current chunk is sealed and a new one started — even if it has fewer
than N sentences.  Sentences longer than the cap on their own are split at word
boundaries.

Best for: mixed corpora with highly variable sentence lengths, cases where
downstream token limits need to be respected strictly.

---

## Parameters

| Parameter | Default | CLI flag | Description |
|---|---|---|---|
| `chunking_strategy` | `sentence_group` | `--chunking` | Strategy: `sentence_group`, `semantic`, `hybrid` |
| `chunk_size` | `512` | `--chunk-size` | Hard character cap per chunk |
| `sentences_per_chunk` | `4` | — | Sentences per group (`sentence_group` / `hybrid`) |
| `max_chunks_per_entry` | `3` | `--max-chunks` | Maximum chunks emitted per diary entry |

No overlap is applied between chunks.  Each chunk is a distinct, non-repeating
window of the source text.

---

## Chunk Selection

After chunking, trivial fragments are discarded and the survivor list is capped
at `max_chunks_per_entry`:

1. **Filter** — chunks shorter than 10 characters, bare ordinal dates (e.g.
   `"3rd"`), and single-character tokens are dropped
   (`is_meaningless_fragment()`).
2. **Cap** — if more than `max_chunks_per_entry` chunks survive, the first
   chunk is always kept (it carries the entry's opening context); the remaining
   slots are filled with the longest remaining chunks, prioritising information
   density.

---

## Chunk Metadata

Each chunk is written as a Markdown file with a YAML frontmatter block:

```markdown
---
source_file: /path/to/diary.txt
entry_index: 12
chunk_index: 0
timestamp: 2024-06-15T09:30
category: work
context: Work
---
<chunk text>
```

| Field | Source | Purpose |
|---|---|---|
| `source_file` | diary file path | Full provenance back to the original file |
| `entry_index` | parser output | Which entry within the file |
| `chunk_index` | chunker output | Position within the entry (0-based) |
| `timestamp` | diary entry header | When the entry was written |
| `category` | classifier | Semantic topic (e.g. `work`, `social`, `finance`) |
| `context` | NLP rules | Coarse context label (`Work`, `Home`, `Social`, `Reflection`, `Emotion`, `General`) |

This metadata is preserved in the SQLite graph node and is returned on every
query/pack result, enabling filtered retrieval by time range, category, or
context.

---

## Classification

Topic classification runs before chunking finalises chunk objects, assigning
two labels to each `EntryChunk`.

**`semantic_category`** is discovered unsupervised via TF-IDF vectorisation +
k-means clustering (default 10 clusters).  If a supervised `TopicClassifier` is
available it takes precedence, with the unsupervised path as fallback.

**`context_classification`** is assigned by lightweight NLP rules over the
chunk text.  spaCy named-entity recognition and keyword heuristics map chunks
to one of six coarse labels: `Work`, `Home`, `Social`, `Reflection`, `Emotion`,
`General`.

---

## Storage Layout

```
<repo_root>/
└── .diarykg/
    ├── corpus/                     ← chunk Markdown files
    │   ├── entry_0000_chunk_00.md
    │   ├── entry_0000_chunk_01.md
    │   └── ...
    ├── graph.sqlite                ← DocKG node/edge graph
    ├── lancedb/                    ← semantic vector index
    └── config.json                 ← build parameters (strategy, chunk_size, …)
```

`config.json` records the exact build parameters so that snapshots can
reproduce the conditions under which the KG was constructed.

---

## Choosing a Strategy

| Situation | Recommended strategy |
|---|---|
| General diary corpus | `sentence_group` |
| Academic or long-form documents | `semantic` |
| Mixed corpora, strict token budgets | `hybrid` |
| Fastest possible indexing | `sentence_group` |
| Best topic boundary precision | `semantic` |

When in doubt, start with `sentence_group` (the default) and run
`kgrag snapshot` before and after switching strategies to compare node counts
and retrieval quality in the snapshot delta.
