TITLE OF THE INVENTION

SYSTEM AND METHOD FOR FEDERATED RETRIEVAL-AUGMENTED GENERATION OVER
STRUCTURALLY DERIVED HETEROGENEOUS KNOWLEDGE GRAPHS

CROSS-REFERENCE TO RELATED APPLICATIONS

Not Applicable.

STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

THE NAMES OF THE PARTIES TO A JOINT RESEARCH AGREEMENT

Not Applicable.

INCORPORATION-BY-REFERENCE OF MATERIAL SUBMITTED ELECTRONICALLY

Not Applicable.

STATEMENT REGARDING PRIOR DISCLOSURES BY THE INVENTOR OR A JOINT INVENTOR

Not Applicable.

---

BACKGROUND OF THE INVENTION

**Field of the Invention**

The present invention relates to information retrieval systems, and more
particularly to methods and systems for constructing, indexing, and
federating multiple heterogeneous knowledge graphs derived from formally
structured source artifacts, and for exposing the federated knowledge base
to artificial intelligence agents through a uniform programmatic interface.

**Description of the Related Art**

Large-scale information retrieval systems that support artificial intelligence
synthesis face a fundamental challenge: source knowledge exists in many
incompatible forms. Software systems encode behavior in programming language
source code. Scientific knowledge is encoded in domain-specific formats such as
biochemical pathway databases, protein structure data banks, and ontological
schemas. Legal knowledge is encoded in hierarchical statute structures.
Personal knowledge is encoded in diary entries, correspondence, and biographical
records. Cultural knowledge is encoded in scriptural hierarchies and annotated
texts. These representations are maintained separately, queried through
incompatible interfaces, and cannot be searched simultaneously.

The predominant prior-art solution is Retrieval-Augmented Generation (RAG),
which embeds all source documents into a vector index and retrieves documents
by semantic similarity. This approach discards the formal structure of
structured source artifacts. A Python call graph, a metabolic pathway
traversal, a statutory cross-reference chain, and a protein bond topology are
all structural properties that cannot be recovered by vector search over
source text. Vector retrieval approximates topical relevance but does not
expose the structural relationships that define the meaning of formally
specified artifacts.

An alternative approach, described in Edge et al., "From Local to Global: A
Graph RAG Approach to Query-Focused Summarization" (arXiv:2404.16130, 2024),
uses a large language model to extract a knowledge graph from unstructured
text. This approach recovers some relational structure but the structure is
probabilistically inferred rather than deterministically derived: entity
extraction may introduce errors, edges may be hallucinated, and the resulting
graph cannot be independently verified against a formal source specification.
Furthermore, this approach requires a large language model at graph construction
time, introducing computational cost, rate-limit dependency, and non-determinism
into what could otherwise be a deterministic compilation step.

Single-domain structural analysis tools exist for specific source types.
Integrated development environments parse abstract syntax trees to support code
navigation. Document management systems maintain section hierarchies for
structured documents. Bioinformatics tools maintain pathway and structure
databases. However, no prior art provides a uniform interface through which
heterogeneous structural knowledge graphs of fundamentally different kinds —
code graphs, document graphs, biochemical graphs, legal graphs, personal
knowledge graphs — can be queried simultaneously through a single federated
interface, with results globally ranked and returned with full source
provenance.

There is therefore a need in the art for a system and method that: (a)
constructs knowledge graphs deterministically from the formal structure of
each source domain without requiring language model participation; (b) provides
a uniform five-method adapter protocol through which any structural knowledge
graph can be exposed to a federation layer regardless of its underlying
representation; (c) maintains a hierarchical registry enabling individual
knowledge graph instances to be grouped into named corpora and person-centric
corpora; (d) executes federated semantic queries across all registered
knowledge graphs with global result ranking; (e) performs semantic chunking of
prose corpora using a dynamic statistical threshold based on inter-sentence
embedding similarity; (f) selects representative corpus samples for ingestion
using diversity-preserving clustering in a multi-dimensional feature space; and
(g) captures point-in-time snapshots of knowledge graph state using stable
version-control-derived keys to enable differential queries across knowledge
graph histories.

---

BRIEF SUMMARY OF THE INVENTION

The present invention provides a federated knowledge graph retrieval system,
termed KGRAG, comprising a uniform adapter protocol, a hierarchical registry,
a federated query orchestrator, a semantic chunking subsystem, a
diversity-preserving ingestion pipeline, a snapshot subsystem, and a
machine-communication protocol server.

In one aspect, the invention provides a computer-implemented system for
federated knowledge graph retrieval, comprising: a plurality of knowledge graph
adapters each implementing a common abstract interface comprising at minimum
availability verification, semantic query, snippet extraction, statistics
retrieval, corpus analysis, and point-in-time snapshot methods; a registry
storing metadata for each registered knowledge graph instance; a federation
orchestrator configured to resolve registered instances, dispatch queries to
each available adapter, and globally rank aggregated results; and a
machine-communication protocol server exposing the federated query surface to
external agents.

In another aspect, the invention provides a computer-implemented method for
constructing and querying a federated knowledge base, comprising:
deterministically deriving structural knowledge graphs from formally specified
source artifacts by application of domain-specific parsers operating on the
formal grammar or ontological schema of each source domain; storing each
derived knowledge graph in a graph storage layer comprising a node-edge
relational database indexed by a co-located semantic vector index; registering
each knowledge graph instance in a persistent registry along with its kind,
repository path, database paths, version, and metadata; and, upon receiving a
query, dispatching the query to all available registered knowledge graph
instances, collecting scored results, and returning a globally ranked unified
result set with full source provenance.

In a further aspect, the invention provides a computer-implemented method for
semantically segmenting prose text into index units, comprising: tokenizing
the input text into sentences using a natural language processing model;
encoding each sentence into a dense vector representation using a sentence
encoder model; computing the pairwise cosine similarity between each adjacent
pair of sentence vectors to produce a similarity sequence; computing a dynamic
segmentation threshold equal to the arithmetic mean of the similarity sequence
minus one standard deviation of the similarity sequence; inserting segment
boundaries at each position where the similarity falls below the threshold;
and enforcing a maximum character length constraint on resulting segments by
word-boundary subdivision.

In a still further aspect, the invention provides a computer-implemented method
for selecting a representative sample of entries from a corpus for incremental
ingestion, comprising: extracting a multi-dimensional feature vector for each
corpus entry, the feature vector comprising temporal features derived from the
entry's timestamp and linguistic features derived from natural language
processing analysis of the entry's content; normalizing the feature matrix by
subtracting the column mean and dividing by the column standard deviation;
partitioning the normalized feature matrix into a target number of clusters
using k-means clustering; and selecting, from each cluster, the entry whose
normalized feature vector has the minimum Euclidean distance to the cluster
centroid.

In yet another aspect, the invention provides a computer-implemented method for
capturing and comparing point-in-time states of a knowledge graph, comprising:
computing a stable content-addressable identifier for the current state of the
source corpus by executing a version-control tree-hash command; capturing
node count, edge count, and domain-specific metrics from the knowledge graph at
the time of capture; computing a quantitative delta between the captured
metrics and the metrics of the chronologically preceding snapshot; persisting
the snapshot record to a file named after the content-addressable identifier;
and updating a manifest index enabling retrieval of any historical snapshot by
its identifier.

---

BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 is a block diagram illustrating the layered architecture of the federated
knowledge graph retrieval system.

FIG. 2 is a class diagram illustrating the KGAdapter abstract interface and
its concrete implementations for each supported knowledge graph kind.

FIG. 3 is a data flow diagram illustrating the federated query algorithm
executed by the KGRAG orchestrator.

FIG. 4 is a schema diagram illustrating the three-level hierarchical registry
comprising the KGRegistry, CorpusRegistry, and PersonCorpusRegistry.

FIG. 5 is a flow diagram illustrating the semantic chunking method using the
dynamic cosine-similarity threshold.

FIG. 6 is a flow diagram illustrating the diversity-preserving corpus sampling
method using k-means clustering in normalized feature space.

FIG. 7 is a flow diagram illustrating the snapshot capture and differential
computation method using version-control tree hashes.

FIG. 8 is a system diagram illustrating integration of the machine-communication
protocol server with external AI agent clients.

FIG. 9 is a screen layout diagram illustrating the four-tab interactive
visualization application, showing the Registry browser, federated query
interface with real-time hit rendering, analysis panel, and snippet pack
editor with token budget display.

FIG. 10 is a three-dimensional rendering diagram illustrating the abstract
syntax tree visualizer for Python code knowledge graphs, showing the module
hierarchy as an interactive spatial tree with nodes classified by entity kind
and edges representing structural relationships.

---

DETAILED DESCRIPTION OF THE INVENTION

The following detailed description sets forth specific embodiments of the
invention with reference to the accompanying figures. Like reference numerals
refer to like elements throughout.

**I. SYSTEM ARCHITECTURE OVERVIEW**

Referring to FIG. 1, the system is organized into five abstraction layers, each
with a single responsibility and depending only on layers below it.

Layer 1, the Source Parsing Layer, comprises domain-specific parsers that
operate on formally specified source artifacts to produce typed nodes and edges.
For Python source code, Layer 1 comprises an abstract syntax tree extractor
performing two deterministic passes over all `.py` files in a repository: a
first pass extracting definition nodes (functions, classes, modules) and
structural edges (`CONTAINS`, `IMPORTS`, `INHERITS`); and a second pass
extracting the call graph and data-flow edges (`CALLS`, `READS`, `WRITES`,
`ATTR_ACCESS`). A post-build symbol resolution step emits `RESOLVES_TO` edges
connecting call-site stubs to first-party definitions. For Markdown and
reStructuredText documentation, Layer 1 comprises a document parse tree
extractor emitting six node kinds: `document`, `section`, `chunk`, `entity`,
`keyword`, and `topic`, connected by eight edge types including `CONTAINS`,
`REFERENCES`, and `SEMANTICALLY_LINKS`. For diary and journal corpora, Layer 1
comprises the semantic chunking subsystem described in Section V below. For
domain-specific corpora including biochemical pathway databases, protein
structure data files, legal statute hierarchies, and scripture verse
hierarchies, Layer 1 comprises domain-specific parsers operating on the formal
schema or grammar of each respective domain.

Layer 2, the Graph Storage Layer, comprises a SQLite relational database
storing typed nodes and edges. Each node record stores a stable string
identifier, a kind label, a name, and a JSON metadata blob. Each edge record
stores a source node identifier, a relation name, a destination node identifier,
and optional JSON evidence. In a preferred embodiment, node identifiers are
constructed deterministically from the kind, source file path, and qualified
name of the entity represented by the node, for example
`fn:src/orchestrator.py:KGRAG.query`, such that identifiers are stable across
rebuilds and directly linkable to their source location.

Layer 3, the Semantic Indexing Layer, comprises a vector database storing
dense vector representations of each node. In a preferred embodiment, the
vector database is LanceDB and the embedding model is a sentence transformer
model such as `all-MiniLM-L6-v2`. The semantic index reads nodes from the graph
storage layer, constructs a canonical text string for each node comprising the
node name and available descriptive text, encodes the text using the embedding
model, and stores the resulting vectors. The semantic index is derived from the
graph storage layer and is fully disposable and rebuildable. Its sole function
is to identify a short ordered list of seed node identifiers by semantic
similarity to a query string; all structural operations are performed in Layer 2.

Layer 4, the Adapter Protocol Layer, comprises the KGAdapter abstract interface
described in Section II below, providing a uniform boundary between all
domain-specific components in Layers 1-3 and all domain-agnostic components in
Layer 5.

Layer 5, the Federation Layer, comprises the KGRAG orchestrator, the three-level
hierarchical registry, the machine-communication protocol server, and the
command-line interface, all described in subsequent sections. Every component
in Layer 5 interacts exclusively with Layer 4 and has no knowledge of any
domain-specific representation.

**II. THE KGADAPTER ABSTRACT INTERFACE**

Referring to FIG. 2, the KGAdapter abstract interface is an abstract base class
defining seven methods, six of which are abstract and must be implemented by
each concrete adapter subclass, and one of which is concrete and provides
functionality derived from the abstract `stats` method.

The `__init__` method receives a KGEntry instance as its sole parameter. The
KGEntry instance stores the registry metadata for the knowledge graph instance
served by the adapter, including the name, kind, repository path, virtual
environment path, optional SQLite database path, optional LanceDB directory
path, version string, list of tags, and a metadata dictionary.

The `is_available` abstract method takes no parameters and returns a Boolean
value. An implementation must return True if and only if: (a) the domain-
specific library backing the knowledge graph is importable in the current
Python environment; and (b) at least one of the knowledge graph's database
files, as specified by the `sqlite_path` or `lancedb_path` fields of the
associated KGEntry, exists on the file system. This method enables the
federation layer to determine which knowledge graph instances are queryable
without instantiating their backing libraries.

The `query` abstract method accepts a natural language query string `q` and
an integer `k` specifying the maximum number of results to return, defaulting
to eight. An implementation must embed `q` using the semantic index to identify
at most `k` seed nodes, expand from those seeds through the graph storage layer
using bounded breadth-first search, rank the reached nodes by a deterministic
composite key comprising hop distance and embedding distance, and return a list
of CrossHit objects. Each CrossHit object stores the knowledge graph name, kind,
node identifier, entity name, entity kind, relevance score, summary text, and
source file path.

The `pack` abstract method accepts a natural language query string `q`, an
integer `k`, and an integer `context` specifying the number of lines of source
context to include around each result, defaulting to five. An implementation
must execute the same seed selection and graph expansion as `query`, then extract
the actual source text at each retained node's verified file path and line span,
and return a list of CrossSnippet objects. Each CrossSnippet object stores the
knowledge graph name, kind, node identifier, source file path, extracted content,
relevance score, and optional start and end line numbers.

The `stats` abstract method takes no parameters and returns a dictionary. An
implementation must return at minimum the node count and edge count of the
knowledge graph as values associated with the keys `node_count` and
`edge_count`, respectively. Implementations may return additional domain-
specific keys.

The `analyze` abstract method takes no parameters and returns a string. An
implementation must return a Markdown-formatted analytical report describing
the current state of the knowledge graph. The report may include structural
statistics, semantic coverage metrics, topical distribution analyses, and
domain-specific observations.

The `snapshot` abstract method accepts a version string `version` and an
optional label string `label`. An implementation must capture the current state
of the knowledge graph, persist the captured state to durable storage, and
return a serializable dictionary containing at minimum the fields `version`,
`timestamp` as an ISO 8601 UTC datetime string, `node_count` as an integer,
and `edge_count` as an integer.

The `_graph_stats` concrete method takes no parameters and returns a dictionary
containing exactly two keys: `node_count` and `edge_count`, each mapped to an
integer. This method invokes the abstract `stats` method, extracts the values
associated with `node_count` and `edge_count`, converts each to an integer,
substituting zero for any value that cannot be converted, and returns the result.
This method is designated as internal and is used by the federation orchestrator
to aggregate structural graph metrics uniformly across heterogeneous knowledge
graph kinds without being affected by domain-specific keys present in the
`stats` output of individual adapters.

In a preferred embodiment, the system supports ten concrete adapter
implementations corresponding to ten knowledge graph kinds:

(a) CodeKGAdapter (kind: `code`): wraps a CodeKG instance backed by Python
abstract syntax tree extraction, storing nodes of kinds `module`, `class`,
`function`, `method`, and `symbol` with edges of types `CONTAINS`, `IMPORTS`,
`INHERITS`, `CALLS`, `READS`, `WRITES`, `ATTR_ACCESS`, and `RESOLVES_TO`.

(b) DocKGAdapter (kind: `doc`): wraps a DocKG instance backed by Markdown
document parse tree extraction, storing nodes of kinds `document`, `section`,
`chunk`, `entity`, `keyword`, and `topic`.

(c) MetaKGAdapter (kind: `meta`): wraps a domain-specific orchestrator instance,
in a preferred embodiment targeting metabolic pathway databases from sources
including KEGG and BioCyc.

(d) DiaryKGAdapter (kind: `diary`): wraps a DiaryKG instance backed by the
semantic chunking subsystem described in Section V, storing diary entry
chunks as document nodes with frontmatter metadata including timestamp,
topic category, and context classification.

(e) VerseKGAdapter (kind: `verse`): targets scripture and verse corpora having
formal `Book -> Chapter -> Verse` hierarchical structure with cross-reference
edges.

(f) MemoryKGAdapter (kind: `memory`): targets episodic memory event graphs
with temporal ordering edges.

(g) DisulfideKGAdapter (kind: `disulfide`): targets disulfide bond networks
derived from protein three-dimensional coordinate data.

(h) PDBFileKGAdapter (kind: `pdbfile`): targets protein structure data bank
files, extracting chains, residues, and structural relationships from ATOM
and SEQRES records.

(i) LegalKGAdapter (kind: `legal`): targets hierarchical legal statute
structures with edges representing cross-references between statutory sections.

(j) PersonKGAdapter (kind: `person`): targets biographical and relational
knowledge graphs derived from personal records.

A StubKGAdapter concrete subclass provides default implementations of all
abstract methods for adapter kinds whose backing libraries are not yet
installed. The stub implementations return empty lists from `query` and
`pack`, return availability status from `stats`, return a structured
unavailability notice from `analyze`, and return a minimal dictionary with
current metrics from `snapshot`. This enables new knowledge graph kinds to
be registered, grouped into corpora, and included in registry operations
before their domain-specific libraries are implemented.

An adapter factory function `make_adapter` accepts a KGEntry instance and
returns the appropriate concrete adapter subclass instance by mapping the
`kind` field of the KGEntry to its corresponding adapter class.

**III. THE HIERARCHICAL REGISTRY SYSTEM**

Referring to FIG. 4, the hierarchical registry system comprises three
interdependent registry components sharing a single SQLite database file,
the path of which defaults to `~/.kgrag/registry.sqlite` and may be
overridden by the `KGRAG_REGISTRY` environment variable.

**III.A. The KGRegistry**

The KGRegistry maintains a table named `kg_entries` having the following
schema: a primary key column `id` of type TEXT storing a UUID version 4
string; a unique column `name` of type TEXT; a column `kind` of type TEXT
storing the string value of a KGKind enumeration member; a column `repo_path`
of type TEXT; a column `venv_path` of type TEXT; nullable columns
`sqlite_path` and `lancedb_path` of type TEXT; a column `version` of type
TEXT defaulting to `'unknown'`; columns `tags` and `metadata` of type TEXT
storing JSON-serialized arrays and objects, respectively; and columns
`created_at` and `updated_at` of type TEXT storing ISO 8601 datetime strings.
Two indices are maintained: `idx_kind` on the `kind` column and `idx_name`
on the `name` column.

The KGRegistry provides `register`, `unregister`, `get`, `find_by_name`,
`find_by_repo`, `list`, `update`, and `stats` operations. The `register`
operation performs an `INSERT OR REPLACE` SQL statement, updating the
`updated_at` timestamp when replacing an existing entry. The `list` operation
accepts an optional `kind` parameter and returns all matching entries
deserialized into KGEntry dataclass instances. The `stats` operation returns
a RegistryStats dataclass instance comprising the total count, a dictionary
mapping each KGKind string to its entry count, the count of entries having
at least one existing database file, and the registry database path.

**III.B. The CorpusRegistry**

The CorpusRegistry maintains a table named `corpora` in the same SQLite
database file as the KGRegistry. The `corpora` table schema comprises: a
primary key column `id` of type TEXT storing a UUID; a unique column `name`
of type TEXT; a column `description` of type TEXT; a column `kg_ids` of type
TEXT storing a JSON-serialized array of KGEntry UUID strings; columns `tags`
and `metadata` of type TEXT storing JSON; and columns `created_at` and
`updated_at` of type TEXT. An index `idx_corpus_name` is maintained on the
`name` column.

A CorpusEntry dataclass instance stores a corpus name, UUID, list of KGEntry
UUID strings, description, tags, timestamps, and metadata dictionary. The
`size` property of CorpusEntry returns the count of KGEntry UUIDs in the
`kg_ids` list.

The CorpusRegistry provides a `resolve_kg_entries` method that accepts a
corpus name and a KGRegistry instance, retrieves the KGEntry UUID list from
the corpus record, resolves each UUID to a KGEntry instance through the
KGRegistry, and returns the list of resolved KGEntry instances, silently
omitting any UUIDs that no longer correspond to registered entries.

**III.C. The PersonCorpusRegistry**

The PersonCorpusRegistry maintains a table named `person_corpora` in the
same SQLite database file. The `person_corpora` table schema extends the
`corpora` schema with personal metadata columns: `birth_year` of type
INTEGER, nullable; `birth_date` of type TEXT, nullable; `address`, `email`,
`phone`, and `notes` of type TEXT with empty string defaults. A
PersonCorpusEntry dataclass instance stores all fields of a CorpusEntry plus
the personal metadata fields.

**IV. THE KGRAG FEDERATION ORCHESTRATOR**

Referring to FIG. 3, the KGRAG orchestrator is the cross-knowledge-graph
federation component. It is initialized with an optional registry database
path and a Boolean `strict` flag defaulting to False. On initialization, it
instantiates one KGRegistry, one CorpusRegistry, and one PersonCorpusRegistry
sharing the same database file, and initializes an empty adapter cache
dictionary mapping knowledge graph instance names to KGAdapter instances.

**IV.A. Adapter Resolution and Lazy Caching**

The `_get_adapter` method implements lazy adapter instantiation with
availability verification. When called with a KGEntry instance, the method
first checks the adapter cache for an entry keyed on the knowledge graph
instance name. If no cached adapter is found, the method calls `make_adapter`
with the KGEntry to obtain a concrete adapter instance, then calls
`is_available` on the adapter. If `is_available` returns False and the `strict`
flag is True, the method raises an ImportError. If `is_available` returns False
and the `strict` flag is False, the method returns None, causing the calling
method to silently skip the unavailable knowledge graph instance. If
`is_available` returns True, the adapter is stored in the cache and returned.

The `_resolve_entries` method accepts an optional sequence of KGKind
enumeration members. If no filter is provided, the method returns all entries
from the KGRegistry. If a filter is provided, the method iterates over the
provided KGKind values, retrieves all entries of each kind from the
KGRegistry, and returns the concatenated list.

**IV.B. The Federated Query Algorithm**

The `query` method of the KGRAG orchestrator implements the federated query
algorithm as follows. The method accepts a natural language query string `q`,
an integer `k` specifying the maximum number of results per knowledge graph
instance, and an optional kind filter. The method initializes an empty list
`all_hits`, an empty dictionary `by_kg` mapping knowledge graph instance
names to hit lists, and an integer `kgs_queried` initialized to zero. The
method then iterates over all resolved KGEntry instances. For each entry, the
method calls `_get_adapter` to obtain a cached or newly instantiated adapter,
skipping entries for which no available adapter can be obtained. For each
available adapter, the method calls `adapter.query(q, k=k)`, appends the
returned CrossHit list to `all_hits`, stores the list in `by_kg` keyed on
the entry name, and increments `kgs_queried`. After all entries have been
processed, the method sorts `all_hits` by score in descending order and
returns a CrossQueryResult dataclass instance storing the query string, the
sorted hit list, the per-instance hit dictionary, the total hit count, and
the count of queried instances.

**IV.C. The Federated Snippet Pack Algorithm**

The `pack` method implements federated snippet extraction using the same
iteration and dispatch structure as the `query` method, calling
`adapter.pack(q, k=k, context=context)` on each available adapter. After
collecting all CrossSnippet objects, the method sorts them by score in
descending order and computes an approximate token count by summing, for each
snippet, the product of the whitespace-split word count of the snippet content
and the factor 4/3. The method returns a CrossSnippetPack dataclass instance
storing the query string, the sorted snippet list, the approximate token
count, and the count of queried instances. The CrossSnippetPack provides a
`render` method that formats the snippet list as a Markdown string, with each
snippet preceded by a section header identifying the source domain, knowledge
graph instance name, file path, and line span.

**IV.D. Corpus-Scoped and Person-Scoped Operations**

The KGRAG orchestrator provides corpus-scoped variants `query_corpus`,
`pack_corpus`, and `stats_corpus`, each accepting a corpus name as the first
parameter. These methods call `_resolve_corpus_entries` to obtain the list
of KGEntry instances associated with the named corpus through the
CorpusRegistry, then execute the same query, pack, or stats logic restricted
to those entries.

The orchestrator provides person-scoped variants `query_person`,
`pack_person`, and `stats_person`, each accepting a person name as the first
parameter. These methods call `_resolve_person_entries` to obtain the list
of KGEntry instances associated with the named person corpus through the
PersonCorpusRegistry, then execute the same logic restricted to those entries.

**V. THE SEMANTIC CHUNKING SUBSYSTEM**

Referring to FIG. 5, the semantic chunking subsystem segments prose corpus
entries into knowledge graph index units using one of three selectable
strategies: `sentence_group`, `semantic`, and `hybrid`.

**V.A. Common Preprocessing**

For all three strategies, the segmentation function first applies a temporal
preamble extractor to identify and remove any timestamp prefix of the form
`Today, YYYY-MM-DDTHH:MM,` from the beginning of the input text, retaining
the preamble for metadata purposes while excluding it from the chunk content.
The remaining text is then tokenized into sentences using a spaCy natural
language processing model, in a preferred embodiment `en_core_web_sm`. Empty
sentences are filtered from the resulting sentence list.

**V.B. The `sentence_group` Strategy**

The `sentence_group` strategy partitions the sentence list into contiguous
groups of a configurable number of sentences `n`, defaulting to four.
Consecutive sentences at indices `i` through `i+n-1` are joined by single
space characters to form one chunk. This strategy produces chunks of
predictable length and is the default strategy for the system.

**V.C. The `semantic` Strategy**

The `semantic` strategy identifies topically coherent segment boundaries
using inter-sentence embedding similarity. If the sentence list contains one
or fewer sentences, the strategy falls back to word-boundary subdivision at
the maximum character length. Otherwise, the strategy encodes all sentences
into dense vector representations using a sentence transformer model, in a
preferred embodiment `all-MiniLM-L6-v2` from the `sentence-transformers`
library. For each adjacent pair of sentence vectors at indices `i` and `i+1`,
the strategy computes the cosine similarity as the dot product of the two
vectors divided by the product of their L2 norms. The resulting similarity
sequence has length one less than the sentence count.

The strategy then computes a dynamic segmentation threshold equal to the
arithmetic mean of the similarity sequence minus one standard deviation of
the similarity sequence:

    threshold = mean(similarities) - std(similarities)

Segment boundaries are inserted at every index `i+1` where the similarity
between sentences `i` and `i+1` is less than the threshold. This threshold
formula places segment boundaries at positions where the inter-sentence
similarity is statistically below the typical similarity for the corpus
entry, corresponding to points of topical transition. The resulting segments
are joined by single spaces to form candidate chunks, and any candidate chunk
exceeding the maximum character length is further subdivided at word boundaries.

**V.D. The `hybrid` Strategy**

The `hybrid` strategy combines the group-size control of `sentence_group` with
the hard character cap enforcement of word-boundary subdivision. The strategy
iterates over the sentence list, accumulating sentences into a current chunk
until one of two flush conditions is met: either the count of sentences in
the current chunk reaches the target group size `n`, or adding the next
sentence would cause the total character count of the current chunk to exceed
the maximum character length. In either case, the accumulated sentences are
joined and appended as a complete chunk and accumulation begins anew. A
sentence whose character count alone exceeds the maximum length is
independently subdivided at word boundaries and its parts appended as
separate chunks.

**V.E. Post-Segmentation Filtering and Selection**

After segmentation by any strategy, candidate chunks are filtered by a
meaningless fragment detector. A chunk is identified as a meaningless fragment
and discarded if its stripped length is less than ten characters, or if it
matches the regular expression for a bare ordinal date such as `"3rd"`, or if
it consists of a single character or digit. After filtering, if the number of
remaining chunks exceeds a configurable maximum chunks per entry parameter,
the first chunk is retained unconditionally; the remaining slots are filled by
selecting the longest remaining chunks by character count in descending order
until the maximum is reached.

**V.F. Chunk Metadata**

Each surviving chunk is written as a Markdown file with a YAML frontmatter
block storing six metadata fields: `source_file` containing the source
corpus file path; `entry_index` containing the zero-based index of the source
entry within the file; `chunk_index` containing the zero-based position of
the chunk within the entry; `timestamp` containing the ISO 8601 datetime of
the source entry; `category` containing the topic category label assigned by
the classifier subsystem; and `context` containing a coarse context
classification label selected from the set {`Work`, `Home`, `Social`,
`Reflection`, `Emotion`, `General`}. Topic category labels are assigned by
a TF-IDF vectorization and k-means clustering classifier applied to the full
set of chunks, with an optional supervised classifier taking precedence when
available. Context classification labels are assigned by a rule-based spaCy
named-entity recognition and keyword heuristic analyzer.

**VI. THE DIVERSITY-PRESERVING CORPUS SAMPLING SUBSYSTEM**

Referring to FIG. 6, the diversity-preserving corpus sampling subsystem
selects a representative subset of corpus entries for a single ingestion run
from among the entries not yet indexed by the knowledge graph, using k-means
clustering in a normalized multi-dimensional feature space.

**VI.A. Feature Extraction**

For each corpus entry, the subsystem extracts a feature vector comprising
nine scalar features. The linguistic features are: `length`, the character
count of the entry content; `sentences`, the sentence count produced by
spaCy tokenization; `entities`, the count of named entities recognized by the
spaCy model; `nouns`, the count of tokens with NOUN part-of-speech tag; `verbs`,
the count of tokens with VERB part-of-speech tag; and `proper_nouns`, the count
of tokens with PROPN part-of-speech tag. The temporal features are:
`timestamp_days`, the POSIX timestamp of the entry divided by 86400; `year`,
the year component of the entry timestamp; `month`, the month-of-year component;
and `day_of_month`, the day-of-month component. Feature extraction is
parallelizable across multiple worker processes using Python's multiprocessing
interface. Extracted feature matrices are cached to disk as serialized
DataFrames keyed on a hash of the source file path to avoid redundant
recomputation across ingestion runs.

**VI.B. Normalization**

The feature matrix, having one row per corpus entry and one column per
feature, is normalized by subtracting the column mean and dividing by the
column standard deviation, producing a zero-mean, unit-variance normalized
matrix. Missing values in the normalized matrix are substituted with zero
before clustering.

**VI.C. Cluster-Centroid Selection**

The normalized matrix is partitioned into `k` clusters using the k-means
algorithm initialized with a configurable random seed, where `k` is set to
the minimum of the target sample count and the total entry count. For each
cluster `i`, the subsystem identifies all row indices assigned to that
cluster, computes the Euclidean distance from each such row to the centroid
of cluster `i`, and selects the entry corresponding to the row with the
minimum distance. The selected entry is the entry in the cluster that is most
representative of the cluster's centroid in the normalized feature space.
The collection of one representative entry per cluster constitutes the
selected sample, which has exactly `k` entries and spans the full temporal
and thematic range of the available unindexed corpus.

**VI.D. Resumable State Management**

The subsystem maintains a state file storing the set of entry index positions
that have been successfully indexed in previous ingestion runs. When
incremental ingestion is invoked with the `resume` flag set to True, the
subsystem loads the state file, filters the full corpus entry list to retain
only entries whose index positions are not present in the state file, and
applies the cluster-centroid selection to the filtered list. After a
successful ingestion run, the state file is updated to include the index
positions of all newly indexed entries. This enables progressive indexing of
large corpora across multiple runs, with each run contributing a diverse
sample of the unindexed portion and the indexed corpus remaining queryable
throughout.

**VII. THE SNAPSHOT SUBSYSTEM**

Referring to FIG. 7, the snapshot subsystem captures point-in-time records of
knowledge graph state, persists them to a content-addressable file store, and
supports computation of quantitative deltas between any two snapshots.

**VII.A. Content-Addressable Snapshot Keys**

Each snapshot is identified by a stable content-addressable key derived from
the version-control state of the source corpus. In a preferred embodiment, the
key is obtained by executing the version-control command
`git rev-parse HEAD^{tree}`, which returns the SHA-1 hash of the Git tree
object corresponding to the working tree state at the HEAD commit. This tree
hash is stable with respect to branch operations, rebases, and commit
message amendments that do not alter file content, making it a reliable
identifier for a specific corpus state independent of the commit history.

**VII.B. Snapshot Metrics**

A DiarySnapshotMetrics record captures: `chunk_count` as the count of indexed
chunk files; `entry_count` as the count of source diary entries; `node_count`
and `edge_count` as the structural counts from the knowledge graph storage
layer; `topic_counts` as a dictionary mapping each topic category label to
its chunk count; `context_counts` as a dictionary mapping each context
classification label to its chunk count; `temporal_span` as a dictionary
storing the ISO 8601 datetime strings of the earliest and latest entries in
the indexed corpus; `chunking_strategy` as the name of the chunking strategy
used to build the corpus; and `chunk_size` as the maximum character length
parameter used.

A DiarySnapshot record stores the snapshot metrics together with the content-
addressable tree hash key, the version string, an ISO 8601 UTC timestamp, the
version-control branch name, an optional human-readable label, the source
file path, and delta records comparing the captured state to the immediately
preceding snapshot and to the baseline snapshot.

**VII.C. Delta Computation**

For each new snapshot, the subsystem locates the chronologically immediately
preceding snapshot and the chronologically oldest snapshot in the manifest.
A DiarySnapshotDelta record is computed for each comparison as a set of
integer differences: the difference in `chunk_count`, the difference in
`entry_count`, the difference in `node_count`, and the difference in
`edge_count`, computed as the new snapshot value minus the reference snapshot
value. Positive values indicate growth; negative values indicate reduction.

**VII.D. Manifest Index**

All snapshots are indexed in a manifest file stored at the path
`.diarykg/snapshots/manifest.json`. The manifest stores a format version
string, a last-update timestamp, and an array of summary records, one per
snapshot, each containing the tree hash key, branch name, capture timestamp,
version string, optional label, snapshot file name, summary metrics, and
delta records. The manifest enables O(1) lookup of any snapshot by its key
without loading the full snapshot record, and O(n) enumeration of all
snapshots in chronological order. Individual snapshot records are stored as
JSON files named `{tree_hash}.json` in the `.diarykg/snapshots/` directory.

**VIII. THE MACHINE-COMMUNICATION PROTOCOL SERVER**

Referring to FIG. 8, the machine-communication protocol (MCP) server wraps
the KGRAG orchestrator and exposes its full operational surface as a
collection of callable tools conforming to the Model Context Protocol
specification. The MCP transport uses standard input/output streams, making
the server compatible with any MCP-capable client including Claude Code, Kilo
Code, GitHub Copilot extensions using the MCP interface, Cline, and Claude
Desktop, without requiring network configuration.

The MCP server exposes twenty-two tools organized into three groups:

Registry tools: `kgrag_stats`, returning a registry summary including total
count, per-kind breakdown, and built count; `kgrag_list`, accepting an
optional kind filter and returning the list of registered knowledge graph
instances; `kgrag_info`, accepting a name or UUID and returning full entry
detail; `kgrag_query`, accepting a query string, optional result count, and
optional kind filter and executing the federated query algorithm; and
`kgrag_pack`, accepting a query string, optional result count, optional
context window, and optional kind filter and executing the federated snippet
pack algorithm.

Corpus tools: `kgrag_corpus_list`, `kgrag_corpus_info`, `kgrag_corpus_create`,
`kgrag_corpus_delete`, `kgrag_corpus_add`, `kgrag_corpus_remove`,
`kgrag_corpus_query`, and `kgrag_corpus_pack`, providing creation, management,
and scoped query operations for named corpus groups.

Person corpus tools: `kgrag_person_list`, `kgrag_person_info`,
`kgrag_person_create`, `kgrag_person_delete`, `kgrag_person_add`,
`kgrag_person_remove`, `kgrag_person_update`, `kgrag_person_query`, and
`kgrag_person_pack`, providing creation, management with personal metadata
fields, and scoped query operations for person-centric corpus groups.

**X. THE INTERACTIVE VISUALIZATION SUBSYSTEM**

The system provides two distinct interactive visualization components, each
rendering a different facet of the knowledge graph: a web-based federated
query and analysis dashboard targeting the semantic layer, and a three-
dimensional abstract syntax tree renderer targeting the structural layer of
Python code knowledge graphs.

**X.A. The Semantic-Layer Web Dashboard**

Referring to FIG. 9, the semantic-layer web dashboard is implemented as a
Python web application using the Streamlit framework. The application receives
a KGRAG orchestrator instance at startup and maintains the orchestrator as
shared state across all user sessions.

The application presents four tabs: Registry, Federated Query, Analysis, and
Snippet Pack.

The Registry tab displays a summary table of all registered knowledge graph
instances retrieved from the KGRegistry, listing the name, kind, version,
repository path, and tag list for each entry. Below the table, the tab
presents live structural statistics for each knowledge graph instance whose
adapter is available, including the node count and edge count obtained by
invoking `_graph_stats` on the corresponding adapter without instantiating
unnecessary library components.

The Federated Query tab presents a text input for the query string, a numeric
input for the maximum result count `k` defaulting to eight, and a multi-select
widget for optional kind filtering. On submission, the tab invokes the
orchestrator's `query` method synchronously and renders each returned CrossHit
as a styled card. Each card displays the hit's knowledge graph name, entity
name, entity kind, source file path, relevance score rendered as a
proportional horizontal score bar, and the summary text. Cards are color-coded
by knowledge graph kind: code-kind hits are rendered in blue, doc-kind hits in
green, and meta-kind hits in purple. Node-kind sub-classification uses a
secondary color palette: module nodes in dark blue, class nodes in teal,
function nodes in medium blue, method nodes in cyan, chunk nodes in dark
green, section nodes in green, and entity nodes in olive. The total result
count and count of queried knowledge graph instances are displayed as a
summary line above the result cards.

The Analysis tab presents a select box populated with the names of all
registered knowledge graph instances whose adapters are available. On
selection, the tab invokes the adapter's `analyze` method and renders the
returned Markdown string using the Streamlit Markdown renderer, preserving
headings, tables, and code blocks.

The Snippet Pack tab presents the same query input and kind filter controls
as the Federated Query tab, plus a context window numeric input defaulting to
five lines. On submission, the tab invokes the orchestrator's `pack` method
and displays the returned snippets. The tab displays an approximate token
budget gauge computing the sum of per-snippet word counts multiplied by 4/3
and presenting the total against a configurable token budget threshold. The
tab provides download buttons exporting the snippet collection as a Markdown
string produced by `CrossSnippetPack.render()` and as a JSON serialization
of the CrossSnippetPack dataclass, enabling downstream LLM context injection
workflows.

`CrossSnippetPack.render()` formats the snippet list as a Markdown document.
The method constructs a section header for each snippet in the format
`## [kind:name] path:line-endline`, where `kind` is the knowledge graph kind
string, `name` is the knowledge graph instance name, `path` is the source
file path, and `line` and `endline` are the start and end line numbers of
the extracted source text. The snippet content is placed in a fenced code
block following the header. This format encodes full source provenance in a
human-readable, parseable header suitable for injection into LLM context
windows with citation support.

**X.B. Semantic Enrichment of Chunk Metadata**

Prior to embedding, each chunk produced by the semantic chunking subsystem
is enriched with two classification labels that are stored in the YAML
frontmatter of the chunk file.

The first label, `category`, is a topic category label assigned by a
two-stage classifier pipeline. In the first stage, TF-IDF vectorization is
applied to all chunks in the corpus, producing a term-frequency matrix.
K-means clustering is applied to the TF-IDF matrix with a configurable number
of clusters, and each cluster is assigned a label derived from its highest-
weight terms. Each chunk is assigned the label of its cluster. In the second
stage, when a supervised topic classifier model is available, its
classifications take precedence over the unsupervised cluster labels.

The second label, `context`, is a coarse context classification label
selected from the fixed vocabulary {`Work`, `Home`, `Social`, `Reflection`,
`Emotion`, `General`}. Assignment is performed by a rule-based analyzer
using spaCy named-entity recognition and keyword heuristics: the presence of
organization and person entities combined with task-related keywords triggers
the `Work` label; location entities combined with domestic keywords trigger
`Home`; person entities without organizational context trigger `Social`;
first-person subjective constructs trigger `Reflection` or `Emotion`
depending on emotional term density; and unclassified chunks receive the
`General` label.

These enriched labels are stored as metadata within the knowledge graph node
records and are available as filterable fields in registry queries and
diagnostic analytics.

**X.C. The Three-Dimensional Abstract Syntax Tree Renderer**

Referring to FIG. 10, the three-dimensional abstract syntax tree renderer
visualizes the structural layer of a Python code knowledge graph as an
interactive spatial scene. The renderer is implemented using the PyVista
scientific visualization library with the PyVistaQt backend for hardware-
accelerated rendering, and is additionally accessible as a browser-embedded
scene via the trame-vtk web interface.

The renderer reads the node and edge tables directly from the code knowledge
graph's SQLite database. Each node is assigned a three-dimensional spatial
position computed by a layered hierarchical layout algorithm: module nodes
are placed at the root level at evenly spaced angular positions on a
horizontal plane; class nodes are placed in a second tier centered beneath
their parent module node; function and method nodes are placed in lower tiers
centered beneath their parent class or module node; and symbol nodes are
placed at the leaf tier. Layer separation and radial spread are parameterized
by the depth of the subtree rooted at each node, ensuring that dense subtrees
do not overlap their neighbors.

Each node is rendered as a geometric primitive whose shape and color encode
the node kind: module nodes as large grey spheres, class nodes as medium
blue spheres, function nodes as medium green spheres, method nodes as small
cyan spheres, and symbol nodes as small white points. Structural edges are
rendered as line segments with colors corresponding to the edge relation type:
`CONTAINS` edges in light grey, `CALLS` edges in orange, `IMPORTS` edges
in yellow, and `INHERITS` edges in purple.

The scene supports interactive pan, rotate, and zoom via mouse controls.
Clicking on a node displays a sidebar showing the node's identifier, kind,
name, source file path, line span, and docstring summary. The renderer
provides a callable interface accepting a query string: when invoked, the
renderer highlights nodes semantically related to the query by computing the
cosine similarity between the query embedding and stored node embeddings,
increasing the rendered size of high-similarity nodes and dimming unrelated
nodes, enabling visual exploration of which code entities are most relevant
to a given question.

**IX. ALTERNATIVE EMBODIMENTS**

In alternative embodiments, the graph storage layer may use a graph database
management system such as Neo4j, ArangoDB, or Amazon Neptune in place of
SQLite, with corresponding modifications to the graph storage interface.

In alternative embodiments, the semantic indexing layer may use a vector
database other than LanceDB, including Chroma, Pinecone, Weaviate, or FAISS,
with corresponding modifications to the semantic index interface.

In alternative embodiments, the sentence transformer model used for semantic
chunking and semantic indexing may be replaced by any model producing dense
vector representations of fixed dimensionality, including domain-specific
fine-tuned models.

In alternative embodiments, the k-means clustering algorithm used for
diversity-preserving corpus sampling may be replaced by other clustering
algorithms including DBSCAN, agglomerative hierarchical clustering, or
Gaussian mixture model clustering, subject to adaptation of the centroid
selection step.

In alternative embodiments, the version-control tree hash used as the snapshot
key may be replaced by a cryptographic hash of the corpus file contents, or
by a monotonically increasing sequence number, subject to loss of the
content-addressability property described in Section VII.A.

In alternative embodiments, the machine-communication protocol server may
expose its tools over a network transport such as HTTP with Server-Sent Events
in place of standard input/output streams.

---

CLAIM OR CLAIMS

**Claim 1.**
A computer-implemented system for federated retrieval over a plurality of
heterogeneous knowledge graphs, the system comprising:
  a processor and a non-transitory computer-readable medium storing
  instructions that, when executed by the processor, cause the system to:
  maintain a registry database storing, for each of a plurality of registered
  knowledge graph instances, a registry entry comprising a name, a kind
  selected from a set of enumerated domain kinds, a repository path, a
  database path, and a version identifier;
  instantiate, for each registered knowledge graph instance, a corresponding
  adapter object implementing a uniform abstract interface, the abstract
  interface comprising at minimum:
    a first method configured to return a Boolean value indicating whether the
    knowledge graph instance is available for querying,
    a second method configured to accept a natural language query string and a
    result count, query the knowledge graph instance using semantic embedding-
    based seed selection followed by structural graph traversal, and return a
    ranked list of hit objects each carrying a node identifier, a source file
    path, a relevance score, and a knowledge graph kind indicator,
    a third method configured to accept a natural language query string and
    extract source text snippets at verified file paths and line spans, and
    a fourth method configured to return a dictionary of graph topology counts
    comprising at minimum a node count and an edge count;
  receive a query string;
  iterate over all registered knowledge graph instances, dispatching the query
  string to each adapter object for which the first method returns True;
  collect hit objects returned by all dispatched adapter objects into an
  aggregate hit list; and
  sort the aggregate hit list in descending order of relevance score and return
  the sorted list together with provenance metadata identifying the originating
  knowledge graph instance for each hit.

**Claim 2.**
The system of claim 1, wherein the abstract interface further comprises a
fifth method configured to accept a version string and an optional label
string, capture the current node count, edge count, and domain-specific
metrics of the knowledge graph instance as a snapshot record, persist the
snapshot record to durable storage, and return a serializable dictionary
containing at minimum the version string, an ISO 8601 UTC timestamp, the
node count, and the edge count.

**Claim 3.**
The system of claim 1, wherein the abstract interface further comprises a
sixth concrete method that invokes the fourth method, extracts the node count
and edge count values from the returned dictionary, converts each value to an
integer, substitutes zero for any value that cannot be converted to an integer,
and returns a dictionary consisting of exactly the node count and edge count
as integers, the sixth method being called by the federation layer to aggregate
graph topology metrics uniformly across knowledge graph instances of differing
kinds without being affected by domain-specific keys in the fourth method
output.

**Claim 4.**
The system of claim 1, wherein the set of enumerated domain kinds comprises
at least: a code kind designating a knowledge graph derived from programming
language abstract syntax trees; a doc kind designating a knowledge graph
derived from structured document parse trees; a meta kind designating a
knowledge graph derived from domain-specific ontological schemas; a diary kind
designating a knowledge graph derived from temporally ordered prose entries;
a legal kind designating a knowledge graph derived from hierarchical statute
structures; and a verse kind designating a knowledge graph derived from
hierarchical scripture or verse structures.

**Claim 5.**
The system of claim 1, wherein instantiating an adapter object comprises:
checking whether a cached adapter object for the knowledge graph instance is
stored in an adapter cache; if a cached adapter object is found, returning
the cached adapter object; if no cached adapter object is found, constructing
a new adapter object of the class corresponding to the kind of the knowledge
graph instance, invoking the first method of the new adapter object, and if
the first method returns True, storing the new adapter object in the adapter
cache keyed on the knowledge graph instance name and returning the stored
object; and if the first method returns False, returning a null value causing
the knowledge graph instance to be silently excluded from the current
federated query.

**Claim 6.**
The system of claim 1, wherein the registry database further stores a corpus
table maintaining named groupings of registered knowledge graph instances,
each corpus record comprising a corpus name, a universally unique identifier,
and a list of knowledge graph instance identifiers; and wherein the system
is further configured to, upon receiving a corpus-scoped query comprising a
corpus name and a query string, resolve the corpus name to the list of
knowledge graph instance identifiers stored in the corpus table, restrict the
iteration over registered knowledge graph instances to the resolved instances,
and execute the federated query over the restricted set.

**Claim 7.**
The system of claim 6, wherein the registry database further stores a person
corpus table extending the corpus table with personal metadata fields
comprising at minimum a birth year field, an address field, an email address
field, and a notes field; and wherein the system is further configured to
execute person-scoped federated queries restricted to the knowledge graph
instances associated with a named person corpus entry.

**Claim 8.**
The system of claim 1, further comprising a machine-communication protocol
server configured to expose the federated query capability as a set of callable
tools accessible to external artificial intelligence agent clients over a
standard input/output transport, the set of callable tools comprising at
minimum a tool for executing a federated semantic query and returning ranked
results, a tool for executing a federated snippet pack and returning extracted
source text, and a tool for returning registry statistics.

**Claim 9.**
A computer-implemented method for constructing an index unit from a prose
corpus entry for storage in a knowledge graph, the method comprising:
  tokenizing an input text string into a sentence list using a natural language
  processing model;
  encoding each sentence in the sentence list into a dense vector
  representation using a sentence encoder model to produce an embedding matrix;
  computing, for each adjacent pair of sentences at indices i and i+1 in the
  sentence list, a cosine similarity value equal to the dot product of the
  embeddings at indices i and i+1 divided by the product of their respective
  L2 norms, to produce a similarity sequence;
  computing a segmentation threshold equal to the arithmetic mean of the
  similarity sequence minus one standard deviation of the similarity sequence;
  inserting a segment boundary between sentences i and i+1 at each index
  position where the corresponding similarity value is less than the
  segmentation threshold; and
  joining sentences within each resulting segment by whitespace to produce
  a candidate chunk, and enforcing a maximum character length on each
  candidate chunk by word-boundary subdivision.

**Claim 10.**
The method of claim 9, wherein the dynamic segmentation threshold is computed
as:

    threshold = (1/N) * sum(s_i) - sqrt((1/(N-1)) * sum((s_i - mean)^2))

where N is the length of the similarity sequence, s_i is the i-th similarity
value, and mean is the arithmetic mean of the similarity sequence; whereby the
threshold adapts to the characteristic similarity distribution of each
individual corpus entry rather than to a fixed global constant.

**Claim 11.**
The method of claim 9, further comprising, after producing candidate chunks:
  discarding each candidate chunk whose stripped character count is less than
  ten, or which matches a pattern for a bare ordinal date expression, or which
  consists of a single character;
  if the count of remaining candidate chunks exceeds a maximum chunks per
  entry parameter, retaining the first remaining candidate chunk unconditionally
  and filling remaining slots by selecting candidate chunks in descending order
  of character count until the maximum is reached; and
  annotating each surviving chunk with a frontmatter metadata block comprising
  the source file path, source entry index, chunk position index, source entry
  timestamp, a topic category label, and a context classification label.

**Claim 12.**
The method of claim 9, wherein the method is one of three selectable
segmentation strategies, the other two strategies comprising:
  a sentence-group strategy that partitions the sentence list into contiguous
  groups of a configurable number of sentences without computing embeddings or
  similarities; and
  a hybrid strategy that partitions the sentence list into groups of the
  configurable number of sentences subject to a hard maximum character length
  constraint enforced by word-boundary subdivision.

**Claim 13.**
A computer-implemented method for selecting a representative sample from a
corpus for incremental knowledge graph ingestion, the method comprising:
  filtering a full corpus entry list to produce an unindexed entry list by
  removing corpus entries whose index positions are recorded as already indexed
  in a persistent state file;
  extracting, for each entry in the unindexed entry list, a feature vector
  comprising temporal features derived from the entry timestamp and linguistic
  features derived from applying a natural language processing model to the
  entry content;
  constructing a feature matrix having one row per unindexed entry and one
  column per feature;
  normalizing the feature matrix by subtracting the column mean and dividing
  by the column standard deviation;
  partitioning the normalized feature matrix into a target count of clusters
  using k-means clustering;
  selecting, from each cluster, the entry corresponding to the row of the
  normalized feature matrix having the minimum Euclidean distance to the
  cluster centroid; and
  after successful ingestion, updating the persistent state file to record the
  index positions of the selected entries.

**Claim 14.**
The method of claim 13, wherein the temporal features comprise a timestamp
expressed in fractional days since the Unix epoch, a year value, a month-of-
year value, and a day-of-month value; and wherein the linguistic features
comprise a character count, a sentence count, a named entity count, a noun
token count, a verb token count, and a proper noun token count.

**Claim 15.**
The method of claim 13, wherein selecting the entry from each cluster
comprises:
  for each cluster index i, identifying all row indices in the normalized
  feature matrix assigned to cluster i by the k-means algorithm;
  for each identified row index, computing the Euclidean distance between the
  normalized feature vector at that row and the centroid vector of cluster i;
  selecting the entry at the row index having the minimum computed Euclidean
  distance; and
  returning a sample list consisting of exactly one selected entry per cluster,
  whereby the sample spans the temporal range and thematic diversity of the
  unindexed corpus regardless of corpus size.

**Claim 16.**
A computer-implemented method for capturing and comparing point-in-time states
of a knowledge graph derived from a version-controlled source corpus, the
method comprising:
  obtaining a content-addressable identifier for the current state of the
  source corpus by executing a version-control system command that returns a
  hash of the current working-tree state independent of commit identifiers;
  capturing, from the knowledge graph storage layer, a node count and an edge
  count representing the current structural state of the knowledge graph;
  capturing domain-specific metrics comprising at minimum a source entry count
  and an indexed chunk count;
  constructing a snapshot record comprising the content-addressable identifier,
  an ISO 8601 UTC timestamp, the captured node count, edge count, and domain-
  specific metrics, a version string, and an optional human-readable label;
  computing a delta record by subtracting the node count, edge count, entry
  count, and chunk count of the chronologically immediately preceding snapshot
  from the corresponding values of the constructed snapshot record;
  persisting the snapshot record as a file named after the content-addressable
  identifier in a designated snapshots directory; and
  updating a manifest index file stored in the snapshots directory with a
  summary of the new snapshot including the content-addressable identifier,
  timestamp, version string, and delta record.

**Claim 17.**
The method of claim 16, wherein the content-addressable identifier is obtained
by executing the command `git rev-parse HEAD^{tree}`, which returns the SHA-1
hash of the Git tree object at the HEAD commit, the tree hash being stable
across branch operations, rebases, and commit message modifications that do
not alter the content of the version-controlled files.

**Claim 18.**
The method of claim 16, further comprising performing a differential query
comprising:
  receiving two content-addressable identifiers designating a first snapshot
  and a second snapshot;
  loading the first snapshot record and the second snapshot record from the
  snapshots directory;
  executing a federated semantic query against the knowledge graph as indexed
  at the state represented by the first snapshot;
  executing the same federated semantic query against the knowledge graph as
  indexed at the state represented by the second snapshot;
  computing the set difference of the top-k results of the two queries; and
  returning the entries present in the second query result but absent from the
  first query result as representing knowledge that entered the indexed corpus
  between the two snapshot states.

**Claim 19.**
A computer-implemented system for interactive visualization of a federated
knowledge graph registry, the system comprising:
  a web dashboard process configured to receive a KGRAG orchestrator instance
  at startup and present a multi-tab user interface comprising:
    a registry tab displaying a tabular summary of all registered knowledge
    graph instances including per-instance structural statistics obtained by
    invoking a normalized graph statistics method on each available adapter;
    a federated query tab providing a query input, a result count input, and
    an optional domain-kind filter, wherein submitting the query tab invokes
    the orchestrator's federated query method and renders each returned result
    as a styled card comprising the entity name, entity kind, source file
    path, a proportional horizontal relevance score bar, a summary text
    display, and a color code indicating the knowledge graph domain kind;
    an analysis tab providing a selector populated with available knowledge
    graph instance names and rendering the Markdown analysis report returned
    by the selected adapter's analysis method; and
    a snippet pack tab providing a query input and a context window input,
    wherein submitting the snippet pack tab invokes the orchestrator's snippet
    pack method and displays an approximate token budget gauge, and provides
    export controls for downloading the snippet collection as a Markdown
    string with per-snippet section headers encoding source domain, instance
    name, file path, and line span, and as a JSON serialization.

**Claim 20.**
A computer-implemented method for three-dimensional structural visualization
of a Python code knowledge graph, the method comprising:
  reading node records and edge records from a code knowledge graph storage
  layer, the node records comprising at minimum an identifier, a kind label,
  a name, a source file path, and line span fields;
  assigning each node a three-dimensional spatial position using a layered
  hierarchical layout algorithm in which module nodes are placed at a root
  layer, class nodes are placed in a second layer centered beneath their
  parent module nodes, function and method nodes are placed in lower layers
  centered beneath their parent class or module nodes, and symbol nodes are
  placed at a leaf layer, with layer separation and radial spread parameterized
  by the depth of the subtree rooted at each node;
  rendering each node as a geometric primitive whose shape and color encode
  the node's kind label, and rendering each edge as a line segment whose
  color encodes the edge relation type;
  responding to a user-supplied query string by computing the cosine
  similarity between the query's dense vector embedding and each node's
  stored dense vector embedding, increasing the rendered size of nodes with
  high cosine similarity, and reducing the rendered opacity of nodes with
  low cosine similarity; and
  displaying a sidebar showing the node identifier, source file path, line
  span, and docstring text of any node selected by user interaction with
  the rendered scene.

**Claim 21.**
A non-transitory computer-readable medium storing instructions that, when
executed by one or more processors, implement a federated knowledge graph
retrieval system comprising:
  a registry module configured to persist, in a relational database,
  registration records for a plurality of knowledge graph instances of
  heterogeneous kinds, each registration record comprising a unique identifier,
  a domain kind indicator, one or more database file paths, and version
  metadata;
  a corpus grouping module configured to persist, in the same relational
  database, named collections of knowledge graph instance identifiers,
  enabling scoped queries restricted to a named subset of the registered
  instances;
  an adapter dispatch module configured to, for each registered knowledge graph
  instance, lazily construct and cache a corresponding adapter object
  implementing a uniform interface, verify the adapter's availability without
  constructing the adapter's backing library if the adapter is already cached,
  and return a null value for instances whose backing library is not installed,
  enabling graceful degradation in the presence of partially deployed
  knowledge graph backends;
  a federation module configured to receive a query string, iterate over
  registered knowledge graph instances, dispatch the query string to each
  available adapter, collect scored results from all adapters, sort the
  collected results in descending order of relevance score, and return the
  globally ranked result list with per-result provenance metadata; and
  a protocol server module configured to expose the federation module's
  query and snippet extraction capabilities as callable tools accessible to
  external AI agent clients over a standard input/output transport.

**Claim 22.**
The non-transitory computer-readable medium of claim 21, wherein the adapter
dispatch module is further configured to, when constructing a new adapter
object for a knowledge graph instance whose backing library is not installed,
construct a stub adapter object that returns an empty list from query and
snippet extraction calls, returns an unavailability status from statistics
calls, returns a structured unavailability notice from analysis calls, and
returns a minimal snapshot dictionary from snapshot calls; whereby a knowledge
graph kind can be registered in the registry and included in corpus groupings
before its domain-specific library is implemented without causing errors in
federation operations.

---

ABSTRACT OF THE DISCLOSURE

A system and method for federated retrieval-augmented generation over
structurally derived heterogeneous knowledge graphs. A uniform adapter
protocol enables knowledge graphs of any domain kind to be queried through a
single federation layer without language model participation in graph
construction. A hierarchical registry stores individual instances, named
corpus groups, and person-centric corpus groups in a relational database. A
federated query orchestrator dispatches queries to all available adapters,
globally ranks results by relevance score, and returns results with full
source provenance including snippet packing for LLM context injection. A
semantic chunking method uses a dynamic threshold equal to the mean minus one
standard deviation of inter-sentence cosine similarities to segment prose at
topical boundaries, enriched with TF-IDF topic categories and named-entity
context labels. A diversity-preserving sampler uses k-means clustering in a
normalized feature space for incremental ingestion. A snapshot subsystem keys
records to version-control tree hashes enabling differential queries. An
interactive web dashboard renders real-time federated query results with
relevance score bars and export for LLM injection. A three-dimensional AST
renderer visualizes Python code graph structure with query-driven node
highlighting.
