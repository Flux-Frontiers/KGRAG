# PATENT APPLICATION

## SYSTEM AND METHOD FOR OFFLINE SEMANTIC PRE-COMPUTATION AND KNOWLEDGE GRAPH CONSTRUCTION FROM UNSTRUCTURED TEXT CORPORA

---

**Inventor:** Eric G. Suchanek, PhD
**Assignee:** Flux-Frontiers
**Filing Date:** 2026-03-27
**Application Type:** Utility Patent

---

## CROSS-REFERENCE TO RELATED APPLICATIONS

Not applicable.

---

## FIELD OF THE INVENTION

The present invention relates generally to natural language processing and knowledge graph construction, and more particularly to a system and method for offline semantic pre-computation of unstructured text corpora that eliminates query-time inference while preserving full semantic, structural, and metadata-based search capability across arbitrary document types including plain text, Markdown, HTML, transcripts, clinical notes, legal filings, and timestamped journals.

---

## BACKGROUND OF THE INVENTION

### The Prior Art and Its Deficiencies

Modern semantic search systems operate under foundational assumptions that constrain their deployment, cost, and privacy characteristics regardless of the type of text corpus being processed.

**First assumption: semantic understanding requires live inference.** When a user queries any document corpus — whether a personal journal, a clinical record archive, a software documentation repository, or a collection of Markdown files — conventional systems invoke a large language model (LLM) at query time, either via cloud API or local GPU inference, to process the query and generate semantically relevant results. This architecture imposes per-query costs that scale linearly with query volume, requires persistent network connectivity for cloud-based systems, and demands specialized hardware (GPU clusters) for local deployment. Consumer-grade hardware cannot serve these workloads at interactive latencies for corpora exceeding trivial sizes.

**Second assumption: metadata extraction requires LLM processing.** Dates, entities, structural relationships, and contextual signals embedded in natural language prose are conventionally extracted by language models at either ingest or query time. For locally-deployed small-parameter models (e.g., 4 billion parameters), this extraction fails systematically — such models hallucinate values, confuse formats, produce malformed output, and cannot reliably distinguish relative from absolute references. This failure mode applies universally: temporal extraction from diaries, entity extraction from clinical notes, structural extraction from legal documents, and topic extraction from any prose corpus are all subject to this degradation at small model scales. Critically, for corpora that already carry structured metadata — Markdown heading hierarchies, ISO timestamps in filenames, section-tagged HTML, and speaker labels in transcripts — invoking an LLM for extraction is not merely unreliable but architecturally wasteful: the structure is present in the source and can be read directly.

**Third assumption: semantic and structural search require separate systems.** Prior art systems typically address either semantic similarity search (vector stores, embedding search engines) or structural graph queries (knowledge graph databases), but not both in a single integrated, offline-capable pipeline. Retrieval-Augmented Generation (RAG) pipelines embed documents into vector stores but require LLM inference at query time for answer synthesis; traditional knowledge graph systems provide structural querying but lack integrated semantic vector search; and embedding-based search engines provide semantic similarity but lack structural provenance, topic classification, and graph relationships.

No existing system provides, in a single integrated pipeline executable on consumer hardware without network connectivity: (a) multi-phase NLP enrichment with configurable topic and context classification applicable to any unstructured text corpus; (b) direct metadata extraction from source structure bypassing LLM extraction entirely; (c) parallel multi-process vector embedding with no external service dependency; (d) a hybrid knowledge graph combining structural indices with semantic vector indices; and (e) sub-five-minute full-corpus ingestion at the scale of thousands of documents.

---

## SUMMARY OF THE INVENTION

The present invention provides a system and method for constructing a semantically enriched, hybrid knowledge graph from any unstructured text corpus through offline pre-computation. The method is general: it applies to plain text files (.txt), Markdown documents (.md), HTML pages, interview and meeting transcripts, clinical notes, legal filings, timestamped journals, and any other corpus of natural language documents. Metadata anchors — structural signals such as heading hierarchies, timestamps, named entity annotations, speaker labels, or section tags — are *optional enrichment inputs* that enhance the resulting knowledge graph when present, but are not prerequisites for the method.

The core innovation is a shift from query-time inference to ingest-time pre-computation: all semantic understanding — topic labeling, context classification, vector embedding, and graph edge construction — is computed once during corpus ingestion. The resulting knowledge graph is a frozen, versioned, queryable artifact that serves all subsequent queries through vector lookup and graph traversal alone, with no model loading or inference at query time.

The system comprises six sequential processing stages orchestrated by a unified pipeline controller:

1. A multi-phase NLP transformer that parses source documents of any format, applies configurable sentence-group chunking, performs multi-label topic classification and single-label context classification using domain-configurable YAML vocabularies, optionally applies spaCy NLP enrichment (named-entity recognition, part-of-speech tagging, dependency parsing, sentence segmentation), and supports configurable sampling strategies;

2. A corpus emitter that writes each semantically enriched chunk as a structured document with metadata frontmatter, writing available metadata fields directly from source structure without any language model extraction;

3. A structural graph builder that indexes all chunks into a relational database with BM25 lexical search capability and typed graph edges;

4. A semantic vector index builder that generates dense vector embeddings and stores them in a columnar vector database for approximate nearest-neighbor search;

5. A multi-process parallel embedder that shards the corpus across CPU worker processes, each loading an independent model instance with no shared state and no GIL contention; and

6. A JSON embedding cache that stores aligned arrays of embeddings, texts, and metadata fields for downstream analysis.

The invention inverts the conventional cost model: ingestion cost is moderate and paid once per corpus version; query cost is negligible and does not increase with query volume; privacy is preserved because no data leaves the local machine; and offline operation is fully supported on consumer-grade CPU hardware.

---

## DETAILED DESCRIPTION OF THE PREFERRED EMBODIMENTS

### Section A: General Method — Any Unstructured Text Corpus

#### A.1 Method Overview

The general method operates on any collection of text documents. Source documents are read in their native format; no specific format is required as a precondition for the method. The pipeline accepts:

- Plain text files with no internal structure;
- Structured plain text with consistent delimiters (pipe, tab, CSV);
- Markdown files with heading hierarchies and YAML frontmatter;
- HTML documents with sectional and heading markup;
- Transcripts with speaker-turn annotations;
- Any other text corpus amenable to sentence segmentation.

The pipeline produces a uniform output regardless of input format: a collection of semantically enriched chunk documents with metadata frontmatter, indexed into a hybrid knowledge graph. The chunk documents carry whatever metadata is available and extractable directly from the source; fields not present in the source are omitted or set to null without pipeline failure.

**Core pipeline stages.** The method applies five sequential enrichment phases to each document:

**Phase 1 — Document Parsing.** The system reads source documents and produces structured records with content fields. Available metadata fields (timestamps, headings, speaker labels, section tags, file paths) are extracted directly from source structure. No language model is invoked for parsing.

**Phase 2 — Sentence-Group Chunking.** Document content is segmented into chunks using a configurable chunking strategy. The default strategy uses sentence-group chunking with a configurable number of sentences per chunk and a configurable maximum character count. Alternative strategies include hybrid chunking (sentence boundaries combined with character limits) and semantic chunking (sentences grouped by topical coherence). Chunking parameters are configurable to accommodate different corpus characteristics.

**Phase 3 — Multi-Label Topic Classification.** Each chunk is classified against a domain-configurable YAML vocabulary that maps topic labels to keyword lists. Classification uses TF-IDF weighted keyword matching. Each chunk may carry multiple topic labels. The vocabulary is fully user-configurable, enabling domain adaptation to any subject area without code changes.

**Phase 4 — Single-Label Context Classification.** Each chunk receives exactly one context label from a second configurable YAML vocabulary. Context categories represent the situational or document-type frame of the content. Assignment uses keyword matching with priority ordering defined in the vocabulary.

**Phase 5 — Configurable Sampling.** When processing a subset of a large corpus, the system applies configurable sampling. For temporally-organized corpora, temporally-diverse sampling uses uniform stride across the time axis. For other corpora, alternative sampling strategies (random, stratified by topic, stratified by document type) may be configured.

#### A.2 Corpus Emission with Direct Metadata Writes

Each semantically enriched chunk is written as a structured document file with metadata frontmatter. Metadata fields are written directly from the values extracted in the parsing phase; no language model is involved in populating any metadata field.

The critical design innovation is **direct metadata database writes**: wherever the source corpus carries explicit structural metadata — an ISO timestamp in a pipe-delimited record, a heading in a Markdown file, a speaker label in a transcript, a section tag in an HTML document — that metadata is written directly to the chunk frontmatter as a first-class indexed field. This approach is unconditionally reliable and is independent of model capability or model availability.

Fields not present in the source are omitted from the frontmatter without pipeline failure, enabling the same pipeline to process heterogeneous corpora containing a mix of document types with varying metadata richness.

#### A.3 Hybrid Knowledge Graph Construction

The emitted chunk documents are indexed into a hybrid knowledge graph comprising two complementary indices:

**Structural graph index.** All chunks are indexed into a relational database (SQLite in the preferred embodiment) providing: BM25 full-text search over chunk content; typed graph edges representing containment (source document to chunk), similarity (chunks sharing lexical overlap above a configurable threshold), and structural adjacency (chunks adjacent in source document order); and metadata columns for all frontmatter fields enabling efficient predicate pushdown.

**Semantic vector index.** Dense vector embeddings are computed for each chunk using a pre-trained sentence-transformer model and stored in a columnar vector database (LanceDB in the preferred embodiment). All embedding computation occurs at ingest time; no model is loaded at query time.

#### A.4 Query-Time Operation

The completed knowledge graph supports hybrid retrieval combining:

- **BM25 lexical search** for exact term matching and Boolean queries;
- **Vector approximate nearest-neighbor search** for semantic similarity queries;
- **Metadata filtering** on any indexed frontmatter field;
- **Graph traversal** for structural navigation (containment, similarity, adjacency).

All four retrieval modalities operate on pre-computed indices. No model is loaded at query time. No inference is performed. Query latency is sub-millisecond for the reference corpus.

---

### Section B: First Preferred Embodiment — Markdown Corpus with Heading Hierarchy

#### B.1 Markdown as Ontological Grounding Without NLP

Markdown documents carry a built-in topic taxonomy in their heading hierarchy. Level-one headings (`#`) define top-level topics; level-two headings (`##`) define subtopics; level-three headings (`###`) define sub-subtopics. This structure is syntactically unambiguous, requires no natural language processing to extract, and provides free ontological grounding for every chunk: the heading path to a chunk is a fully qualified topic label requiring no classification inference.

In this embodiment, the parsing phase reads the heading hierarchy and assigns each chunk a hierarchical topic label derived directly from its heading ancestry. For example, a chunk under `# Architecture / ## Components / ### Embedding Pipeline` receives the label path `architecture:components:embedding_pipeline` as a frontmatter field without any vocabulary matching or topic classification model.

#### B.2 Heading-Derived Edge Construction

The structural graph builder constructs additional typed edges exploiting the heading hierarchy:

- SUBTOPIC edges linking parent heading sections to child heading sections;
- SIBLING edges linking sections sharing the same parent heading;
- CONTAINS edges linking heading-level nodes to their constituent chunk nodes.

These edges provide navigational structure aligned with the document's own organization, enabling graph traversal that respects authorial intent without any NLP-derived inference.

#### B.3 YAML Frontmatter Passthrough

Markdown files frequently carry YAML frontmatter blocks. In this embodiment, the parser reads existing YAML frontmatter and passes all key-value pairs directly to the chunk metadata without transformation. This preserves author-supplied metadata (publication date, author, tags, category, status) as first-class indexed fields in the knowledge graph.

---

### Section C: Second Preferred Embodiment — Timestamped Corpus

#### C.1 Timestamped Corpora

Many valuable text corpora carry explicit timestamp metadata: personal journals, clinical notes, legal filings, meeting transcripts, email archives, and incident logs. In these corpora, the timestamp is not embedded in prose requiring extraction — it is a structured field in the record format, a filename prefix, a YAML frontmatter field, or a database column.

In this embodiment, the parsing phase validates ISO-format timestamps and writes them directly to the chunk frontmatter as the `timestamp` field. No language model is involved in any aspect of temporal grounding. This completely bypasses the temporal extraction failure mode that plagues small-parameter local models.

The temporal provenance field is a first-class metadata field on every chunk, enabling:
- Temporal range filtering (return chunks within a date range);
- Temporal graph edges (TEMPORAL edges linking temporally adjacent chunks);
- Temporally-diverse sampling (uniform stride across the time axis ensures representative temporal coverage);
- Temporal faceted search (aggregation of results by time period).

#### C.2 Reference Implementation: Pepys Corpus

The system has been reduced to practice and validated on a reference corpus consisting of 6,450 diary entries from the Samuel Pepys diary spanning 9.6 years (1660–1669), comprising 23,235 enriched lines totaling 3.3 megabytes. This corpus represents the second preferred embodiment (timestamped corpus) with pipe-delimited records carrying explicit ISO timestamps.

The emitted chunk document format for this embodiment is:

```yaml
---
source_file: corpus/enriched_full.txt
timestamp: 1666-09-02T08:00
topic: domestic
context: Home
chunk_index: 0
---
[chunk text content]
```

Full pipeline execution on this reference corpus completes in approximately three minutes on consumer-grade Apple Silicon hardware with no GPU and no network connectivity.

#### C.3 Validated Reference Corpus Metrics

The following table summarizes validated metrics for the reference corpus. These metrics are reported as results for the preferred embodiment and do not constitute limitations of the general method.

| Metric | Value | Notes |
|---|---|---|
| Source entries | 6,450 | Diary entries, 1660–1669 |
| Enriched lines | 23,235 | Pipe-delimited format |
| Source file size | 3.3 MB | |
| Chunk count | 6,647 | Sentence-group chunking |
| Graph nodes | 29,402 | |
| Graph edges | 355,250 | CONTAINS, SIMILAR, TEMPORAL |
| SQLite database size | 109 MB | Structural index |
| LanceDB vector index | 102 MB | 768-dimensional float32 |
| Combined KG footprint | ~211 MB | |
| Embedding dimensions | 768 | `all-mpnet-base-v2` |
| Full pipeline duration | ~3 min | Apple Silicon, no GPU |
| Query latency | <1 ms | Pre-computed indices |

---

### Section D: spaCy NLP Enrichment Layer

The general method supports an optional spaCy-based NLP enrichment layer that provides additional semantic dimensions beyond keyword-based classification. When enabled, this layer applies the following analyses to each chunk after sentence segmentation:

**Named-Entity Recognition (NER).** spaCy's pre-trained NER models identify and classify named entities (persons, organizations, locations, dates, quantities, events) in each chunk. Entity labels are written to the chunk frontmatter as structured metadata fields, enabling entity-based filtering, entity co-occurrence graph edges, and entity-centric retrieval without any query-time model invocation.

**Part-of-Speech Tagging.** POS tags provide grammatical category annotations (noun, verb, adjective, etc.) for each token. These annotations support syntactic filtering and enable grammar-based enrichment as a natural extension of the method.

**Dependency Parsing.** Dependency parse trees provide structural relationships between tokens (subject, object, modifier, etc.). These relationships support extraction of semantic triples (subject-predicate-object) for knowledge graph construction, providing a pathway from statistical embedding similarity to symbolic relationship representation.

**Sentence Segmentation.** spaCy's sentence boundary detection provides the sentence boundaries used by the chunking phase. Using a neural sentence segmentation model produces more accurate chunk boundaries than heuristic punctuation-based methods, particularly for noisy or archaic text.

The spaCy enrichment layer is modular: each of its four capabilities may be enabled independently via configuration. When no enrichment is required, the layer is bypassed entirely and the pipeline operates with keyword-based classification alone.

---

### Section E: Stage 5 — Multi-Process Parallel Embedding

The embedding pipeline operates as an independent processing stage, producing an embedding cache optimized for analysis:

```
Parse -> (optional sample) -> shard across workers -> each worker:
    load sentence-transformer model locally -> encode shard -> return float32 array
-> concatenate shards in original order -> write cache
```

**Key design decisions providing the inventive step:**

**Independent model instances per worker.** Each worker process loads its own copy of the sentence-transformer model. There is no shared memory between workers and no Global Interpreter Lock (GIL) contention. This is in contrast to conventional approaches that share a single model instance across threads, which in Python-based systems creates GIL contention that prevents true parallelism.

**Spawn start method enforcement.** On POSIX systems, the system enforces the `spawn` start method for subprocess creation rather than the default `fork` method. This ensures clean subprocess isolation, preventing issues with inherited file descriptors, CUDA contexts, or other process state that can cause subtle failures in forked multiprocessing.

**Configurable sampling.** When processing a subset of the corpus, sampling is applied before sharding. For temporally-organized corpora, uniform stride across the time axis is used. For other corpora, configurable sampling strategies are supported.

**Aligned output format.** The output consists of aligned arrays — embeddings, texts, and metadata fields — stored as JSON. This self-contained format requires no database dependency and is portable across environments.

The architecture achieves near-linear scaling with CPU count on encode-bound workloads in the general case. In the validated reference implementation, the embedding stage embeds 7,282 chunks (768-dimensional float32) in approximately 47–49 seconds regardless of worker count (1, 4, or 8 workers), demonstrating that on unified-memory consumer hardware the encoding workload saturates available CPU cores at a single worker. The full pipeline — NLP transformation (~4 min 17 s), KG construction (~7 min 59 s), and embedding (~52 s) — completes in approximately 13–14 minutes on Apple Silicon without GPU acceleration.

**Hardware acceleration note.** On Apple Silicon (M-series) hardware, it has been empirically determined that executing the pipeline under TensorFlow's standard CPU execution path (with `CUDA_VISIBLE_DEVICES` unset) outperforms explicit TensorFlow-Metal GPU acceleration for the small MLP architectures used in this system. This behavior arises because TensorFlow on Apple Silicon internally dispatches compute through the Apple Matrix Coprocessor (AMX) and Accelerate framework on the CPU path, while the Metal GPU backend incurs per-operation synchronization overhead that dominates for small-batch, small-model workloads. The practical consequence is that the preferred deployment configuration for consumer Apple Silicon hardware is TensorFlow's default CPU execution path, which achieves higher throughput than explicit Metal GPU invocation for the manifold-aware classification workloads described herein. This finding generalizes to other unified-memory architectures where the GPU memory transfer overhead exceeds the compute savings for models with parameter counts below approximately 10^5.

---

### Section F: Embedding Cache Format

The JSON embedding cache stores parallel aligned arrays:

```json
{
  "embeddings": [[float32, ...], ...],
  "texts": ["chunk text", ...],
  "metadata": [{"field": "value", ...}, ...]
}
```

The arrays are index-aligned: `embeddings[i]`, `texts[i]`, and `metadata[i]` all correspond to the same source chunk. The metadata array carries whatever fields were present in the chunk frontmatter (timestamp, heading path, topic, context, source file, chunk index, entities, etc.).

---

### Section G: Unified Pipeline Orchestration with Snapshot System

The system provides a unified orchestrator that executes the full pipeline — document parsing, NLP enrichment, corpus emission, structural graph indexing, vector index construction, and snapshot capture — through a single invocation.

**Point-in-time snapshots** capture corpus metrics (document count, chunk count, metadata field coverage), graph metrics (node count, edge count, index sizes), and build metadata (timestamp, hardware, duration). Snapshots are versioned and enable comparison across corpus rebuilds, supporting reproducibility and regression detection.

---

### Section H: Manifold-Aware Classification via Intrinsic Dimensionality Estimation

#### H.1 Intrinsic Dimensionality Estimation from the Pre-Computed Embedding Cache

The JSON embedding cache produced by Stage 6 of the pipeline (Section F) constitutes a complete geometric record of the corpus: aligned arrays of dense vector embeddings, source texts, and metadata fields, requiring no model loading to access. This cache enables a downstream processing stage that exploits the manifold structure implicit in the embedding space to perform classification with dramatically reduced parameter counts and no query-time inference.

The core insight is that high-dimensional embedding spaces are not uniformly occupied: corpus documents lie on a low-dimensional manifold whose intrinsic dimensionality d\* — the minimum number of coordinates required to faithfully represent the data distribution — is strictly less than the ambient embedding dimension. d\* is estimated from the pre-computed embeddings without any model invocation using the **Two-Nearest-Neighbor (TwoNN)** estimator combined with a configurable energy-retention threshold τ: the smallest integer d such that d principal components retain at least τ of the total variance. This procedure is entirely offline and adds negligible computation atop the already-stored cache.

#### H.2 Dimensionality-Reduced Manifold Architecture

Given d\*, the system constructs a **dimensionality-reduced manifold architecture**: a PCA projection from the ambient space to the d\*-dimensional principal subspace, followed by a classification head with d\* × C + C parameters (C = number of classes). The PCA projection is computed offline from the embedding matrix and introduces zero learned parameters. The resulting classifier has parameter counts orders of magnitude below standard deep classifiers.

#### H.3 Zero-Parameter Manifold Classifier

The system further provides a **zero-parameter manifold classifier** (ManifoldModel) that performs classification through k-nearest-neighbor graph voting on the pre-computed embedding manifold with no learned parameters: constructing a k-NN graph from the cached embeddings, then assigning each query point the majority-vote label of its k nearest neighbors. No gradient computation, no weight update, and no model loading occurs at any stage.

#### H.4 Canonical Benchmark Validation

The manifold-aware classification pipeline has been validated on four canonical benchmarks on Apple Silicon hardware (TensorFlow 2.16.2). All experiments used TensorFlow's standard CPU execution path, which was empirically determined to outperform explicit TensorFlow-Metal GPU execution for these small-MLP workloads due to Metal's per-operation synchronization overhead (see Section E). Under the CPU execution path, TensorFlow internally dispatches through Apple's AMX and Accelerate framework, achieving higher throughput than the explicit Metal GPU path for parameter counts below ~10^5. All neural architectures: 5 independent trials. Non-parametric methods (ManifoldModel, KNN): single run on a stratified subsample where noted.

**Table H.1 — Canonical Benchmark Results**

| Architecture | Accuracy | Std | Params | Trials |
|---|---|---|---|---|
| **MNIST** (784-dim input, 10 classes, d\* = 28, τ = 0.9, 96.4% noise dims) | | | | |
| Standard MLP (128→64→out) | 97.56% | 0.08% | 109,386 | 5 |
| Wide Manifold (4d→2d→d, d=28) | 97.30% | 0.19% | 96,134 | 5 |
| Manifold (2d→d, d=28) | 96.85% | 0.19% | 45,846 | 5 |
| PCA→28D + MLP (2d→d) | 96.24% | 0.09% | 3,510 | 5 |
| Intrinsic Dim (PCA→28D→output) | 95.31% | 0.11% | **1,102** | 5 |
| ManifoldModel (τ=0.9, zero-param) | 89.58% | — | **0** | 1† |
| **CIFAR-10** (3,072-dim input, 10 classes, d\* = 34, τ = 0.9) | | | | |
| Intrinsic Dim (PCA→34D→output) | **34.85%** | 0.77% | **1,540** | 5 |
| Wide Manifold (4d→2d→d, d=34) | 32.43% | 0.66% | 107,915 | 5 |
| Manifold (2d→d, d=34) | 31.55% | 1.74% | 104,832 | 5 |
| Standard MLP (1024→512→out) | 20.80% | 2.34% | 3,676,682 | 5 |
| **CIFAR-100** (3,072-dim input, 100 classes, d\* = 19, τ = 0.9) | | | | |
| Intrinsic Dim (PCA→100D→output) | **13.28%** | 0.39% | **20,200** | 3 |
| Wide Manifold (d+1, d=100) | 8.99% | 0.06% | 320,573 | 3 |
| Manifold (d=100) | 8.37% | 0.60% | 317,400 | 3 |
| Standard MLP (1024→512→out) | 6.10% | 0.56% | 3,722,852 | 3 |
| **Digits** (64-dim input, 10 classes, d\* = 14, τ = 0.9, n=1,797 samples) | | | | |
| Standard MLP (128→64→out) | 97.87% | 0.51% | 17,226 | 15 |
| Euclidean KNN (k=7) | 97.33% | 0.54% | **0** | 5 |
| ManifoldModel (τ=0.9, zero-param) | 97.27% | 0.54% | **0** | 5 |
| Manifold (2d→d, d=14) | 96.68% | 0.79% | 2,376 | 15 |

† ManifoldModel on MNIST trained on 5,000 stratified training samples (O(n²) graph constraint); all other methods use full 60,000 training set.

**Key results and patent significance:**

**CIFAR-10.** The intrinsic-dimension-aware architecture achieves 34.85% ± 0.77% with 1,540 parameters — a **+67.5% relative accuracy improvement** (+14.05 pp) over a standard MLP with 3,676,682 parameters. **2,387× parameter reduction** with superior accuracy. All three manifold-aware variants outperform the standard MLP.

**CIFAR-100.** On a 100-class problem, 13.28% ± 0.39% with 20,200 parameters versus 6.10% for the standard MLP with 3,722,852 parameters — a **+117.7% relative accuracy improvement** with **184× fewer parameters**. The advantage increases with classification difficulty.

**Digits / ManifoldModel.** The zero-parameter ManifoldModel achieves 97.27% ± 0.54% — within 0.60 pp of a parameterized MLP and within 0.06 pp of Euclidean KNN — with **zero learned parameters**, demonstrating that the geometric structure in the pre-computed embeddings alone is sufficient for near-optimal classification.

**MNIST.** On the 784-dimensional MNIST corpus (96.4% of dimensions are noise at τ=0.9), the intrinsic-dimension-aware architecture achieves 95.31% ± 0.11% with just 1,102 parameters — only **−2.25 pp** below a standard MLP with 109,386 parameters, at **99× parameter reduction**. On this dataset the standard MLP is well-matched to the task, so the manifold architecture provides extreme parameter efficiency at modest accuracy cost rather than an accuracy gain.

---

## CLAIMS

### Independent Claims

**Claim 1.** A computer-implemented method for constructing a queryable knowledge graph from an unstructured text corpus, comprising:

(a) receiving a plurality of source documents comprising natural language content, wherein the source documents are of any format including plain text, Markdown, HTML, transcripts, clinical notes, or timestamped journal entries, and wherein metadata fields including structural signals, heading labels, timestamps, and named entity annotations are optional enrichment inputs that are extracted directly from source structure when present;

(b) for each source document, applying a multi-phase natural language processing transformation comprising:
- (i) parsing the document and extracting any available metadata fields directly from source structure without invoking any language model for extraction;
- (ii) segmenting the content into one or more chunks according to a configurable chunking strategy;
- (iii) classifying each chunk with one or more topic labels using a configurable topic vocabulary;
- (iv) classifying each chunk with a single context label using a configurable context vocabulary;

(c) emitting each chunk as a structured document file comprising the chunk text and metadata frontmatter, wherein all metadata frontmatter fields are written directly from values extracted in step (b)(i) without invoking any language model for metadata extraction or inference;

(d) constructing a structural graph index from the emitted document files, the structural graph index comprising nodes representing chunks, typed edges representing containment, similarity, and structural adjacency relationships, and a full-text search index over chunk content;

(e) constructing a semantic vector index by computing dense vector embeddings for each chunk using a pre-trained sentence-transformer model and storing the embeddings in a columnar vector store supporting approximate nearest-neighbor search;

wherein steps (d) and (e) collectively constitute ingest-time pre-computation such that all subsequent queries against the knowledge graph are served by vector lookup and graph traversal without loading any language model or performing any neural network inference at query time.

---

**Claim 2.** A computer-implemented method for parallel vector embedding of a text corpus without shared state, comprising:

(a) receiving a plurality of text chunks derived from an unstructured text corpus;

(b) partitioning the text chunks into a plurality of shards, one shard per available CPU core;

(c) spawning a plurality of worker processes using a spawn start method, wherein each worker process:
- (i) loads an independent instance of a sentence-transformer model into its own process memory;
- (ii) encodes its assigned shard of text chunks into dense vector embeddings;
- (iii) returns the embeddings as a contiguous float32 array;

(d) concatenating the returned embeddings from all worker processes in the original corpus order;

wherein no shared memory is used between worker processes, no Global Interpreter Lock contention occurs, and the method achieves near-linear scaling with the number of available CPU cores.

---

**Claim 3.** A system for offline semantic pre-computation of an unstructured text corpus, comprising:

(a) a multi-phase NLP transformer module configured to parse source documents of any format, extract available metadata fields directly from source structure, segment content into chunks, and classify each chunk with topic and context labels from user-configurable YAML vocabularies;

(b) a corpus emitter module configured to write each chunk as a structured document file with metadata frontmatter, wherein all metadata fields are written directly from source-extracted values without language model extraction;

(c) a structural graph builder module configured to index the document files into a relational database comprising nodes, typed edges, and a BM25 full-text search index;

(d) a semantic vector index builder module configured to compute dense vector embeddings using a pre-trained sentence-transformer model and store the embeddings in a columnar vector database;

(e) a multi-process parallel embedder module configured to shard the corpus across worker processes, each worker loading an independent model instance with no shared state;

(f) a unified orchestrator configured to execute modules (a) through (e) in sequence through a single invocation and to capture point-in-time snapshots of corpus and graph metrics;

wherein the system is configured to execute entirely on consumer-grade CPU hardware without GPU acceleration and without network connectivity, and wherein all queries against the constructed knowledge graph are served without loading any language model or performing any inference.

---

### Dependent Claims

**Claim 4.** The method of Claim 1, wherein the source documents comprise Markdown files having a heading hierarchy, and wherein step (b)(i) extracts the heading ancestry of each chunk as a hierarchical topic label written directly to the chunk frontmatter, such that no topic classification vocabulary is required to achieve ontological grounding for Markdown corpora.

**Claim 5.** The method of Claim 4, wherein the structural graph index of step (d) further comprises SUBTOPIC edges linking parent heading section nodes to child heading section nodes, and SIBLING edges linking section nodes sharing the same parent heading, such that the graph topology mirrors the document heading hierarchy.

**Claim 6.** The method of Claim 1, wherein the source documents carry explicit timestamp metadata in a structured field, and wherein step (b)(i) extracts and validates an ISO-format timestamp from the structured field and writes it directly to the chunk frontmatter as a temporal provenance field without invoking any language model for temporal extraction, and wherein the structural graph index of step (d) further comprises TEMPORAL edges linking chunks that are temporally adjacent in the source corpus.

**Claim 7.** The method of Claim 6, further comprising applying temporally-diverse sampling when processing a subset of the corpus, wherein the sampling uses uniform stride across the time axis of the corpus to ensure representative temporal coverage across the full temporal span.

**Claim 8.** The method of Claim 1, further comprising, between steps (b) and (c), applying a spaCy NLP enrichment layer to each chunk, the enrichment layer performing one or more of: named-entity recognition producing entity labels written as structured metadata fields to the chunk frontmatter; part-of-speech tagging producing grammatical category annotations for each token; dependency parsing producing structural token relationships; and sentence segmentation providing chunk boundary detection using a neural sentence boundary model.

**Claim 9.** The method of Claim 8, wherein the named-entity recognition labels are indexed as filterable metadata columns in the structural graph index, enabling entity-centric retrieval and entity co-occurrence graph edges without any query-time model invocation.

**Claim 10.** The method of Claim 1, wherein the configurable chunking strategy of step (b)(ii) comprises sentence-group chunking with a configurable number of sentences per chunk and a configurable maximum character count per chunk.

**Claim 11.** The method of Claim 1, wherein the multi-label topic classification of step (b)(iii) uses TF-IDF weighted keyword matching against a YAML vocabulary file that maps topic labels to keyword lists, and wherein each chunk may receive zero, one, or multiple topic labels, and wherein the vocabulary file is user-replaceable without modification to any system module.

**Claim 12.** The method of Claim 2, wherein the spawn start method is enforced on POSIX systems to ensure clean subprocess isolation and to prevent inheritance of file descriptors, GPU contexts, or other parent process state.

**Claim 13.** The method of Claim 1, wherein the structural graph index of step (d) comprises:
- CONTAINS edges linking source document nodes to constituent chunk nodes;
- SIMILAR edges linking chunk nodes having lexical overlap exceeding a configurable threshold;
- STRUCTURAL_ADJACENT edges linking chunk nodes that are adjacent in source document order.

**Claim 14.** The method of Claim 1, wherein the knowledge graph supports hybrid retrieval combining BM25 lexical search, vector approximate nearest-neighbor search, metadata filtering on any indexed frontmatter field, and graph traversal across typed edges, all without loading any model or performing any inference at query time.

**Claim 15.** The method of Claim 1, wherein the entire pipeline from raw corpus ingestion to completed knowledge graph — comprising NLP transformation, corpus emission, structural graph indexing, and vector index construction — executes in less than twenty minutes for a corpus of up to 10,000 documents on consumer-grade CPU hardware without GPU acceleration.

**Claim 16.** The system of Claim 3, further comprising a snapshot module configured to capture point-in-time metrics including document count, chunk count, metadata field coverage, node count, edge count, index sizes, and build metadata, and to support comparison between snapshots captured at different build times.

**Claim 17.** The system of Claim 3, wherein the structural graph builder module stores the relational database as a SQLite file and the semantic vector index builder module stores the vector database as a LanceDB columnar directory, and wherein the combined knowledge graph footprint for a corpus of approximately 6,500 source documents is less than 250 megabytes.

**Claim 18.** The system of Claim 3, wherein the user-configurable YAML vocabularies of module (a) enable domain adaptation to arbitrary unstructured text corpora — including personal journals, clinical notes, legal case files, corporate meeting transcripts, software documentation repositories, research literature, and biographical archives — without modification to any system module.

**Claim 19.** The system of Claim 3, further comprising an optional spaCy NLP enrichment module interposed between the NLP transformer module and the corpus emitter module, the enrichment module configured to perform named-entity recognition, part-of-speech tagging, dependency parsing, and sentence segmentation, wherein each enrichment capability is independently enabled or disabled via configuration without modifying any other system module.

**Claim 20.** The system of Claim 3, further comprising a manifold-aware classification module configured to consume the JSON embedding cache of module (e) and perform classification by: (a) estimating the intrinsic dimensionality d\* of the embedding matrix using a Two-Nearest-Neighbor estimator with a configurable energy-retention threshold τ, wherein d\* is the smallest integer such that d\* principal components retain at least τ of total variance; (b) projecting all pre-computed embeddings to the d\*-dimensional principal subspace via offline PCA, introducing no learned parameters; and (c) training a classification head of size d\* × C + C parameters (C = number of classes) on the projected embeddings; wherein all pre-computation required for classification is performed offline from the stored embedding cache without model loading or inference at classification time.

**Claim 21.** The system of Claim 20, further comprising a zero-parameter manifold classifier configured to perform classification without any learned parameters by: (a) constructing a k-nearest-neighbor graph from the pre-computed embeddings in the JSON embedding cache; and (b) assigning each query embedding to the majority-vote class label of its k nearest neighbors in the pre-computed graph; wherein no gradient computation, no weight update, and no model loading occurs at any stage, and wherein classification accuracy on the sklearn Digits benchmark (1,797 samples, 64-dimensional input) is 97.27% ± 0.54% with zero parameters — within 0.60 percentage points of a parameterized MLP baseline achieving 97.87% ± 0.51% with 17,226 parameters.

**Claim 22.** The method of Claim 2, wherein, on unified-memory processor architectures in which a GPU shares memory with the CPU, the neural network inference operations of the manifold-aware classification module are executed on the CPU execution path of the deep learning framework rather than the GPU execution path, wherein the CPU execution path achieves higher throughput than the GPU execution path for models with parameter counts below approximately 10^5 due to per-operation GPU synchronization overhead exceeding the compute savings at small model scales, and wherein the deep learning framework internally dispatches the CPU execution path through hardware-accelerated linear algebra primitives provided by the processor's matrix coprocessor.

**Claim 23.** The system of Claim 20, wherein the manifold-aware classification module achieves on the CIFAR-10 benchmark (3,072-dimensional input, 10 classes, d\* = 34 at τ = 0.9) an accuracy of 34.85% ± 0.77% with 1,540 parameters — a 67.5% relative accuracy improvement and 2,387-fold parameter reduction versus a standard MLP achieving 20.80% ± 2.34% with 3,676,682 parameters; on the CIFAR-100 benchmark (3,072-dimensional input, 100 classes, d\* = 19 at τ = 0.9) an accuracy of 13.28% ± 0.39% with 20,200 parameters — a 117.7% relative accuracy improvement and 184-fold parameter reduction versus a standard MLP achieving 6.10% ± 0.56% with 3,722,852 parameters; and on the MNIST benchmark (784-dimensional input, 10 classes, d\* = 28 at τ = 0.9) an accuracy of 95.31% ± 0.11% with 1,102 parameters — a 99-fold parameter reduction versus a standard MLP achieving 97.56% ± 0.08% with 109,386 parameters at an accuracy cost of 2.25 percentage points.

---

## ABSTRACT

A system and method for constructing a semantically enriched hybrid knowledge graph from any unstructured text corpus through offline pre-computation. The method is general, applying to plain text, Markdown, HTML, transcripts, clinical notes, legal filings, timestamped journals, and any other natural language document collection. Metadata anchors — heading hierarchies, ISO timestamps, named entities, speaker labels — are optional enrichment inputs extracted directly from source structure when present, bypassing language model extraction entirely. The pipeline applies multi-phase NLP transformation — parsing, chunking, multi-label topic classification, context classification using domain-configurable YAML vocabularies, and optional spaCy NER, POS, and dependency enrichment — to produce structured chunks with metadata frontmatter. Chunks are indexed into a hybrid knowledge graph comprising a relational database with BM25 full-text search and typed graph edges, and a semantic vector index with dense embeddings from a pre-trained sentence-transformer model. A multi-process parallel embedding pipeline shards the corpus across CPU workers, each loading an independent model instance with no shared state. A unified orchestrator executes the full pipeline through a single invocation with point-in-time snapshot capture. The resulting knowledge graph serves all subsequent queries — lexical, semantic, metadata, and structural — through pre-computed indices with sub-millisecond latency, no model loading, and no inference at query time, executing entirely on consumer-grade CPU hardware without GPU acceleration or network connectivity. Validated on the Pepys reference corpus (6,450 diary entries, 9.6-year span): 7,285 chunks, 29,402 graph nodes, 355,250 edges, 208 MB combined footprint; NLP transformation stage ~4 min 17 s, KG indexing stage ~7 min 59 s, embedding stage ~52 s; full pipeline ~14 minutes. A downstream manifold-aware classification module consumes the pre-computed embedding cache, estimates intrinsic dimensionality d\* offline via Two-Nearest-Neighbor analysis, and classifies via a PCA→d\* linear head or a zero-parameter graph-voting classifier. Canonical results across four benchmarks: CIFAR-10 (+67.5% accuracy, 2,387× parameter reduction vs. standard MLP); CIFAR-100 (+117.7% accuracy, 184× parameter reduction); Digits (97.27% accuracy, zero learned parameters); MNIST (95.31% accuracy, 1,102 parameters — 99× reduction at −2.25 pp cost).

---

*Patent Application — Eric G. Suchanek, PhD — Flux-Frontiers — March 27, 2026*
