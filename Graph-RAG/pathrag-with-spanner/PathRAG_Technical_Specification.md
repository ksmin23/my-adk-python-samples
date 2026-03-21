# PathRAG Technical Specification

- **Source Repository:** [BUPT-GAMMA/PathRAG](https://github.com/BUPT-GAMMA/PathRAG)
- **Analyzed Commit:** [`32567bfc`](https://github.com/BUPT-GAMMA/PathRAG/tree/32567bfc93605b8393996d5fa9ccdc0edbb865b2) (2025-12-17)
- **Initial Document Date:** 2026-03-16
- **Last Updated:** 2026-03-19

## Executive Summary

PathRAG is a **Graph-based Retrieval Augmented Generation (RAG)** system that enhances traditional RAG by introducing **relational path pruning** through knowledge graphs. Unlike standard RAG which retrieves isolated text chunks, PathRAG discovers and leverages **multi-hop semantic paths** between entities to provide richer, more contextually connected answers.

This document provides a technical blueprint for understanding, modifying, or reimplementing PathRAG's core concepts.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Data Structures](#2-core-data-structures)
3. [System Components](#3-system-components)
4. [Indexing Pipeline (Document Ingestion)](#4-indexing-pipeline-document-ingestion)
5. [Query Pipeline (The PathRAG Algorithm)](#5-query-pipeline-the-pathrag-algorithm)
6. [Path Finding & Pruning Algorithm](#6-path-finding--pruning-algorithm)
7. [Prompt Engineering](#7-prompt-engineering)
8. [Configuration Parameters](#8-configuration-parameters)
9. [Adaptation Guide](#9-adaptation-guide)

---

## 1. Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PATHRAG SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        INDEXING PIPELINE                             │   │
│  │                                                                      │   │
│  │   Documents → Chunking → Entity Extraction → Graph Construction      │   │
│  │                              ↓                        ↓              │   │
│  │                    Entity Vector DB        Relationship Vector DB    │   │
│  │                              ↓                        ↓              │   │
│  │                         Knowledge Graph (NetworkX DiGraph)           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         QUERY PIPELINE                               │   │
│  │                                                                      │   │
│  │   Query → Keyword Extraction → Dual Context Retrieval                │   │
│  │                                       ↓                              │   │
│  │                    ┌──────────────────┴──────────────────┐           │   │
│  │                    ↓                                     ↓           │   │
│  │            Low-Level Context                    High-Level Context   │   │
│  │         (Entity-based retrieval)             (Relationship-based)    │   │
│  │                    ↓                                     ↓           │   │
│  │            Direct relationships              PATH FINDING ALGORITHM  │   │
│  │                    ↓                         (1-hop, 2-hop, 3-hop)   │   │
│  │                    └──────────────────┬──────────────────┘           │   │
│  │                                       ↓                              │   │
│  │                              Context Combination                     │   │
│  │                                       ↓                              │   │
│  │                              LLM Response Generation                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Storage Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           STORAGE LAYER                                 │
├──────────────────┬──────────────────────┬───────────────────────────────┤
│   KV Storage     │   Vector Storage     │    Graph Storage              │
├──────────────────┼──────────────────────┼───────────────────────────────┤
│ • full_docs      │ • entities_vdb       │ • chunk_entity_relation_graph │
│ • text_chunks    │ • relationships_vdb  │                               │
│ • llm_cache      │ • chunks_vdb         │                               │
├──────────────────┼──────────────────────┼───────────────────────────────┤
│ JsonKVStorage    │ NanoVectorDBStorage  │ NetworkXStorage               │
│ (file-based)     │ (cosine similarity)  │ (DiGraph + GraphML)           │
└──────────────────┴──────────────────────┴───────────────────────────────┘
```

---

## 2. Core Data Structures

### 2.1 Text Chunk Schema

```python
TextChunkSchema = TypedDict(
    "TextChunkSchema",
    {
        "tokens": int,           # Number of tokens in chunk
        "content": str,          # The text content
        "full_doc_id": str,      # Reference to parent document
        "chunk_order_index": int # Position in original document
    }
)
```

### 2.2 Entity Node Schema

```python
EntityNode = {
    "entity_type": str,     # e.g., "person", "organization", "geo", "event", "category"
    "description": str,     # LLM-generated description of the entity
    "source_id": str        # Chunk IDs where this entity was found (separated by "<SEP>")
}
```

### 2.3 Relationship Edge Schema

```python
RelationshipEdge = {
    "weight": float,        # Relationship strength (summed across occurrences)
    "description": str,     # LLM-generated relationship description
    "keywords": str,        # High-level keywords summarizing the relationship
    "source_id": str        # Chunk IDs where this relationship was found
}
```

### 2.4 Query Parameters

```python
@dataclass
class QueryParam:
    mode: Literal["hybrid"] = "hybrid"           # Query mode
    only_need_context: bool = False              # Return only context, no LLM call
    only_need_prompt: bool = False               # Return the final prompt
    response_type: str = "Multiple Paragraphs"   # Expected response format
    stream: bool = False                         # Stream response
    top_k: int = 40                              # Number of results to retrieve
    max_token_for_text_unit: int = 4000          # Token budget for source texts
    max_token_for_global_context: int = 3000     # Token budget for high-level context
    max_token_for_local_context: int = 5000      # Token budget for low-level context
```

---

## 3. System Components

### 3.1 Component Responsibilities

| Component | File | Purpose |
|-----------|------|---------|
| **PathRAG** | `PathRAG.py` | Main orchestrator class, manages all storage and coordinates pipelines |
| **Chunking** | `operate.py`: `chunking_by_token_size()` | Splits documents into overlapping token-sized chunks |
| **Entity Extraction** | `operate.py`: `extract_entities()` | LLM-based extraction of entities and relationships |
| **KG Query** | `operate.py`: `kg_query()` | Main query handler with keyword extraction and context building |
| **Path Finding** | `operate.py`: `find_paths_and_edges_with_stats()` | **Core PathRAG algorithm** - finds multi-hop paths |
| **Storage Classes** | `storage.py` | KV, Vector, and Graph storage implementations |
| **LLM Integration** | `llm.py` | Provider-agnostic LLM/embedding support via LiteLLM (OpenAI, Gemini, Bedrock, Anthropic, Ollama, etc.) |
| **Prompts** | `prompt.py` | All LLM prompt templates |

### 3.2 Storage Abstractions

```
BaseKVStorage (Abstract)
├── JsonKVStorage         # File-based JSON storage
├── MongoKVStorage        # MongoDB backend
├── OracleKVStorage       # Oracle DB backend
└── TiDBKVStorage         # TiDB backend

BaseVectorStorage (Abstract)
├── NanoVectorDBStorage   # Lightweight local vector DB
├── MilvusVectorDBStorge  # Milvus backend
├── ChromaVectorDBStorage # ChromaDB backend
└── OracleVectorDBStorage # Oracle backend

BaseGraphStorage (Abstract)
├── NetworkXStorage       # In-memory NetworkX DiGraph
├── Neo4JStorage          # Neo4j graph database
├── OracleGraphStorage    # Oracle graph backend
└── AGEStorage            # Apache AGE (PostgreSQL)
```

---

## 4. Indexing Pipeline (Document Ingestion)

### 4.1 Pipeline Flow

```
Input Documents
      │
      ▼
┌─────────────────────────────────────┐
│  Step 1: Document Deduplication     │
│  - MD5 hash each document           │
│  - Skip already indexed docs        │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 2: Chunking                   │
│  - Token-based chunking (1200 tok)  │
│  - Overlap (100 tokens)             │
│  - Track chunk order                │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 3: Entity Extraction          │
│  - LLM extracts entities            │
│  - LLM extracts relationships       │
│  - Multi-gleaning for completeness  │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 4: Knowledge Graph Update     │
│  - Merge duplicate entities         │
│  - Merge duplicate relationships    │
│  - Summarize long descriptions      │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Step 5: Vector DB Indexing         │
│  - Embed entities (name + desc)     │
│  - Embed relationships (keywords)   │
│  - Embed chunks (content)           │
└─────────────────────────────────────┘
```

### 4.2 Chunking Algorithm

```python
def chunking_by_token_size(
    content: str,
    overlap_token_size: int = 128,
    max_token_size: int = 1024,
    tiktoken_model: str = "gpt-4o"
) -> list[dict]:
    """
    Split document into overlapping chunks by token count.

    Algorithm:
    1. Tokenize entire content using tiktoken
    2. Create sliding window with step = (max_token_size - overlap_token_size)
    3. Decode each window back to text
    4. Return list of {tokens, content, chunk_order_index}
    """
    tokens = encode_string_by_tiktoken(content, model_name=tiktoken_model)
    results = []
    step = max_token_size - overlap_token_size

    for index, start in enumerate(range(0, len(tokens), step)):
        chunk_tokens = tokens[start : start + max_token_size]
        chunk_content = decode_tokens_by_tiktoken(chunk_tokens, model_name=tiktoken_model)
        results.append({
            "tokens": len(chunk_tokens),
            "content": chunk_content.strip(),
            "chunk_order_index": index,
        })
    return results
```

### 4.3 Entity Extraction Process

```python
async def extract_entities(chunks, knowledge_graph, entity_vdb, relationships_vdb):
    """
    Multi-gleaning entity extraction from text chunks.

    Process:
    1. For each chunk, send to LLM with entity_extraction prompt
    2. Parse structured output (entities and relationships)
    3. Optionally "glean" again (ask LLM if more entities exist)
    4. Merge duplicate entities across chunks
    5. Merge duplicate relationships
    6. Upsert to graph and vector databases
    """

    for chunk in chunks:
        # Initial extraction
        result = await llm(entity_extraction_prompt.format(chunk.content))

        # Multi-gleaning loop (default: 1 iteration)
        for i in range(max_gleaning):
            glean_result = await llm(continue_extraction_prompt)
            result += glean_result

            # Ask if more entities exist
            if await llm(if_loop_prompt) != "yes":
                break

        # Parse entities: ("entity"<|>NAME<|>TYPE<|>DESCRIPTION)
        # Parse relationships: ("relationship"<|>SRC<|>TGT<|>DESC<|>KEYWORDS<|>WEIGHT)
        entities, relationships = parse_extraction_result(result)

    # Merge and upsert
    for entity_name, entity_occurrences in all_entities.items():
        merged_entity = merge_entity_descriptions(entity_occurrences)
        await knowledge_graph.upsert_node(entity_name, merged_entity)

    for (src, tgt), edge_occurrences in all_relationships.items():
        merged_edge = merge_edge_descriptions(edge_occurrences)
        await knowledge_graph.upsert_edge(src, tgt, merged_edge)
```

### 4.4 Entity/Relationship Merging

When the same entity or relationship is found in multiple chunks:

**Entity Merging:**
- `entity_type`: Most frequent type across occurrences
- `description`: Concatenate all descriptions, then summarize if too long
- `source_id`: Union of all source chunk IDs

**Relationship Merging:**
- `weight`: Sum of all weights (stronger evidence = higher weight)
- `description`: Concatenate and summarize
- `keywords`: Union of all keywords
- `source_id`: Union of all source chunk IDs

---

## 5. Query Pipeline (The PathRAG Algorithm)

### 5.1 Query Flow Overview

```
User Query: "How does A relate to B?"
           │
           ▼
┌──────────────────────────────────────────┐
│  Step 1: Keyword Extraction              │
│  LLM splits query into:                  │
│  - high_level_keywords: themes, concepts │
│  - low_level_keywords: specific entities │
└──────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Step 2: Dual Context Retrieval          │
│                                          │
│  LOW-LEVEL (Local):                      │
│  - Search entity_vdb for low_keywords    │
│  - Get entity nodes and their edges      │
│  - Find connected text chunks            │
│  - **Run PATH FINDING algorithm**        │
│                                          │
│  HIGH-LEVEL (Global):                    │
│  - Search relationship_vdb for keywords  │
│  - Get relationship edges                │
│  - Find connected entities               │
│  - Find source text chunks               │
└──────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Step 3: Context Combination             │
│  - Merge HL and LL entities              │
│  - Merge HL and LL relationships         │
│  - Merge source texts                    │
│  - Format as CSV tables                  │
└──────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Step 4: LLM Response Generation         │
│  - System prompt with context tables     │
│  - User query as input                   │
│  - Generate markdown response            │
└──────────────────────────────────────────┘
```

### 5.2 Keyword Extraction

The query is first decomposed into two types of keywords:

```python
# Example Query: "What is the relationship between Apple and Steve Jobs?"

high_level_keywords = ["Corporate leadership", "Company founding", "Technology industry"]
low_level_keywords = ["Apple", "Steve Jobs", "CEO", "founder"]
```

**High-level keywords** drive relationship-based (global) retrieval.
**Low-level keywords** drive entity-based (local) retrieval.

### 5.3 Context Format

The final context provided to the LLM is structured as CSV tables:

```text
-----global-information-----
-----high-level entity information-----
id,entity,type,description,rank
0,"APPLE","organization","Apple Inc. is a technology company...",45
1,"STEVE JOBS","person","Steve Jobs was co-founder and CEO...",38

-----high-level relationship information-----
id,source,target,description,keywords,weight,rank
0,"STEVE JOBS","APPLE","Founded Apple Computer in 1976","founding, leadership",3.5,83

-----Sources-----
id,content
0,"Steve Jobs and Steve Wozniak founded Apple Computer..."

-----local-information-----
-----low-level entity information-----
id,entity,type,description,rank
...

-----low-level relationship information-----
id,context
0,"The entity STEVE JOBS is a person with description(...)through edge(founded) to connect to STEVE JOBS and APPLE."
```

---

## 6. Path Finding & Pruning Algorithm

### 6.1 The Core Innovation

**This is what makes PathRAG different from standard graph-based RAG.**

Instead of just returning direct entity relationships, PathRAG:
1. Finds ALL paths (1-hop, 2-hop, 3-hop) between retrieved entities
2. Weights paths by traversal frequency using BFS
3. Prunes low-confidence paths using a threshold
4. Generates natural language descriptions of multi-hop connections

### 6.2 Path Finding Algorithm

```python
async def find_paths_and_edges_with_stats(graph, target_nodes):
    """
    Find all paths (up to 3 hops) between target nodes using DFS.

    Args:
        graph: NetworkX graph
        target_nodes: List of entity names from vector search results

    Returns:
        result: Dict mapping (source, target) -> {paths: [...], edges: [...]}
        path_stats: {"1-hop": count, "2-hop": count, "3-hop": count}
        one_hop_paths, two_hop_paths, three_hop_paths: Separate path lists
    """
    result = defaultdict(lambda: {"paths": [], "edges": set()})
    path_stats = {"1-hop": 0, "2-hop": 0, "3-hop": 0}

    async def dfs(current, target, path, depth):
        # Stop at 3 hops maximum
        if depth > 3:
            return

        # Found target - record the path
        if current == target:
            result[(path[0], target)]["paths"].append(list(path))
            # Record all edges in path
            for u, v in zip(path[:-1], path[1:]):
                result[(path[0], target)]["edges"].add(tuple(sorted((u, v))))

            # Categorize by hop count
            if depth == 1:
                path_stats["1-hop"] += 1
                one_hop_paths.append(path)
            elif depth == 2:
                path_stats["2-hop"] += 1
                two_hop_paths.append(path)
            elif depth == 3:
                path_stats["3-hop"] += 1
                three_hop_paths.append(path)
            return

        # Continue DFS to neighbors
        for neighbor in graph.neighbors(current):
            if neighbor not in path:  # Avoid cycles
                await dfs(neighbor, target, path + [neighbor], depth + 1)

    # Find paths between all pairs of target nodes
    for node1 in target_nodes:
        for node2 in target_nodes:
            if node1 != node2:
                await dfs(node1, node2, [node1], 0)

    return result, path_stats, one_hop_paths, two_hop_paths, three_hop_paths
```

### 6.3 Path Weighting with BFS

```python
def bfs_weighted_paths(G, paths, source, target, threshold=0.3, alpha=0.8):
    """
    Weight paths based on traversal frequency using BFS.

    Key insight: Paths that are traversed more frequently (appear in more
    DFS results) are considered more important/confident.

    Parameters:
        threshold: Minimum weight to continue path exploration (0.3)
        alpha: Decay factor for each hop (0.8)

    Algorithm:
    1. Build follow_dict: for each node, which nodes follow it in paths
    2. Starting from source, assign weight 1/num_followers to each edge
    3. Only continue to next hop if weight > threshold
    4. Apply alpha decay at each hop
    5. Return paths with their accumulated weights
    """
    edge_weights = defaultdict(float)
    follow_dict = {}

    # Build follower relationships from all paths
    for p in paths:
        for i in range(len(p) - 1):
            current, next_node = p[i], p[i + 1]
            if current not in follow_dict:
                follow_dict[current] = set()
            follow_dict[current].add(next_node)

    results = []

    # First hop: weight = 1 / number_of_followers
    for neighbor in follow_dict[source]:
        edge_weights[(source, neighbor)] += 1 / len(follow_dict[source])

        if neighbor == target:
            results.append([source, neighbor])
            continue

        # Only continue if edge weight > threshold
        if edge_weights[(source, neighbor)] > threshold:
            # Second hop: apply alpha decay
            for second_neighbor in follow_dict.get(neighbor, []):
                weight = edge_weights[(source, neighbor)] * alpha / len(follow_dict[neighbor])
                edge_weights[(neighbor, second_neighbor)] += weight

                if second_neighbor == target:
                    results.append([source, neighbor, second_neighbor])
                    continue

                # Third hop (if weight still above threshold)
                if edge_weights[(neighbor, second_neighbor)] > threshold:
                    for third_neighbor in follow_dict.get(second_neighbor, []):
                        weight = edge_weights[(neighbor, second_neighbor)] * alpha / len(follow_dict[second_neighbor])
                        edge_weights[(second_neighbor, third_neighbor)] += weight

                        if third_neighbor == target:
                            results.append([source, neighbor, second_neighbor, third_neighbor])

    # Calculate path weights (average edge weight)
    path_weights = []
    for p in paths:
        total_weight = sum(edge_weights.get((p[i], p[i+1]), 0) for i in range(len(p)-1))
        path_weights.append(total_weight / (len(p) - 1))

    return list(zip(paths, path_weights))
```

### 6.4 Path-to-Natural-Language Conversion

```python
async def _find_most_related_edges_from_entities3(node_datas, query_param, knowledge_graph_inst):
    """
    Convert graph paths to natural language relationship descriptions.

    This is the key innovation: instead of returning raw graph data,
    PathRAG generates human-readable path descriptions.
    """

    # 1. Build NetworkX graph from storage
    G = nx.Graph()
    edges = await knowledge_graph_inst.edges()
    nodes = await knowledge_graph_inst.nodes()
    for u, v in edges:
        G.add_edge(u, v)
    G.add_nodes_from(nodes)

    # 2. Find all paths between retrieved entities
    source_nodes = [dp["entity_name"] for dp in node_datas]
    result, path_stats, one_hop_paths, two_hop_paths, three_hop_paths = (
        await find_paths_and_edges_with_stats(G, source_nodes)
    )

    # 3. Weight and prune paths
    threshold = 0.3  # Pruning threshold
    alpha = 0.8      # Hop decay factor

    all_results = []
    for node1 in source_nodes:
        for node2 in source_nodes:
            if node1 != node2 and (node1, node2) in result:
                paths = result[(node1, node2)]["paths"]
                weighted = bfs_weighted_paths(G, paths, node1, node2, threshold, alpha)
                all_results += weighted

    # 4. Sort by weight and deduplicate
    all_results = sorted(all_results, key=lambda x: x[1], reverse=True)
    seen = set()
    result_edge = []
    for edge, weight in all_results:
        sorted_edge = tuple(sorted(edge))
        if sorted_edge not in seen:
            seen.add(sorted_edge)
            result_edge.append((edge, weight))

    # 5. Select top paths (max 15)
    total_edges = min(15, len(results))
    sort_result = result_edge[:total_edges] if result_edge else []
    final_result = [edge for edge, weight in sort_result]

    # 6. Convert to natural language using f-strings
    relationship = []
    for path in final_result:
        if len(path) == 2:
            # 1-hop: A --[relation]--> B
            s_name, t_name = path[0], path[1]
            edge0 = (
                await knowledge_graph_inst.get_edge(path[0], path[1])
                or await knowledge_graph_inst.get_edge(path[1], path[0])
            )
            if edge0 is None:
                continue
            s = await knowledge_graph_inst.get_node(s_name)
            t = await knowledge_graph_inst.get_node(t_name)
            desc = (
                f"The entity {s_name} is a {s['entity_type']} "
                f"with description({s['description']}) "
                f"through edge({edge0['keywords']}) to connect to {s_name} and {t_name}. "
                f"The entity {t_name} is a {t['entity_type']} "
                f"with description({t['description']})"
            )
            relationship.append([desc])

        elif len(path) == 3:
            # 2-hop: A --[rel1]--> B --[rel2]--> C
            s_name, b_name, t_name = path[0], path[1], path[2]
            # ... similar construction with bridge entity

        elif len(path) == 4:
            # 3-hop: A --[rel1]--> B1 --[rel2]--> B2 --[rel3]--> C
            s_name, b1_name, b2_name, t_name = path[0], path[1], path[2], path[3]
            # ... similar construction with two bridge entities

    return relationship[::-1]
```

### 6.5 Pruning Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `threshold` | 0.3 | Minimum edge weight to continue path exploration |
| `alpha` | 0.8 | Decay factor applied at each hop |
| `max_hops` | 3 | Maximum path length to consider |
| `max_paths` | 15 | Maximum number of paths to return |

**Effect of threshold (0.3):**
- Paths with edge weight < 0.3 are pruned
- This eliminates weak/spurious connections
- Higher threshold = stricter pruning, fewer paths

**Effect of alpha (0.8):**
- Each hop reduces confidence by 20%
- 1-hop: weight * 1.0
- 2-hop: weight * 0.8
- 3-hop: weight * 0.64
- Prefers shorter paths over longer ones

---

## 7. Prompt Engineering

### 7.1 Entity Extraction Prompt

```
-Goal-
Given a text document and entity types, identify all entities and relationships.

-Steps-
1. Identify entities with: name, type, description
   Format: ("entity"<|>NAME<|>TYPE<|>DESCRIPTION)

2. Identify relationships with: source, target, description, keywords, strength
   Format: ("relationship"<|>SRC<|>TGT<|>DESC<|>KEYWORDS<|>STRENGTH)

3. Identify content-level keywords
   Format: ("content_keywords"<|>KEYWORDS)

Entity types: [organization, person, geo, event, category]
```

### 7.2 Keyword Extraction Prompt

```
-Role-
Identify high-level and low-level keywords in user queries.

-Goal-
- high_level_keywords: overarching concepts, themes
- low_level_keywords: specific entities, details

Output JSON format:
{
  "high_level_keywords": [...],
  "low_level_keywords": [...]
}
```

### 7.3 RAG Response Prompt

```
-Role-
Answer questions using data from provided tables.

-Goal-
Generate response summarizing information from tables.
Don't make anything up. Say "I don't know" if unsure.

-Data tables-
{context_data}  // CSV formatted context

Style response in markdown.
```

### 7.4 Delimiters

| Delimiter | Value | Purpose |
|-----------|-------|---------|
| Tuple delimiter | `<\|>` | Separates fields within a record |
| Record delimiter | `##` | Separates records in output |
| Completion delimiter | `<\|COMPLETE\|>` | Signals end of extraction |
| Field separator | `<SEP>` | Separates multiple source IDs |

---

## 8. Configuration Parameters

### 8.1 Chunking Parameters

```python
chunk_token_size: int = 1200        # Maximum tokens per chunk
chunk_overlap_token_size: int = 100 # Overlap between consecutive chunks
tiktoken_model_name: str = "gpt-4o-mini"  # Model for tokenization
# Note: tiktoken falls back to cl100k_base encoding for non-OpenAI models
# (e.g. Gemini, Bedrock), providing a reasonable token-count approximation.
```

### 8.2 Entity Extraction Parameters

```python
entity_extract_max_gleaning: int = 1    # Number of "continue extraction" iterations
entity_summary_to_max_tokens: int = 500 # Max tokens for entity descriptions
```

### 8.3 Embedding Parameters

```python
# Embedding model is configured via embedding_model_name and embedding_dim.
# Uses LiteLLM, so any supported provider works.
# Examples:
#   OpenAI  : embedding_model_name="text-embedding-3-small",  embedding_dim=1536
#   Gemini  : embedding_model_name="gemini/gemini-embedding-001", embedding_dim=3072
#   Bedrock : embedding_model_name="bedrock/amazon.titan-embed-text-v2:0", embedding_dim=1024
embedding_model_name: str = "text-embedding-3-small"  # LiteLLM model name
embedding_dim: int = 1536                             # Must match the chosen model
embedding_func: EmbeddingFunc = None                  # Auto-created from above; or pass a custom one
embedding_batch_num: int = 32                         # Batch size for embedding
embedding_func_max_async: int = 16                    # Max concurrent embedding calls
```

### 8.4 LLM Parameters

```python
# LLM is configured via llm_model_func and llm_model_name.
# Default uses LiteLLM (litellm_complete), supporting any provider.
# Examples:
#   OpenAI    : llm_model_name="gpt-4o"
#   Gemini    : llm_model_name="gemini/gemini-2.5-flash"
#   Anthropic : llm_model_name="anthropic/claude-sonnet-4-20250514"
#   Bedrock   : llm_model_name="bedrock/anthropic.claude-3-haiku-20240307-v1:0"
llm_model_func: callable = litellm_complete
llm_model_name: str = "gpt-4o"
llm_model_max_token_size: int = 32768
llm_model_max_async: int = 16
```

### 8.5 Query Parameters

```python
top_k: int = 40                           # Results from vector search
max_token_for_text_unit: int = 4000       # Token budget for sources
max_token_for_global_context: int = 3000  # Token budget for HL context
max_token_for_local_context: int = 5000   # Token budget for LL context
```

### 8.6 Vector DB Parameters

```python
cosine_better_than_threshold: float = 0.2  # Minimum similarity for retrieval
```

---

## 9. Adaptation Guide

### 9.1 Key Concepts to Implement in Your Project

1. **Dual Vector Databases**
   - One for entities (searchable by entity name + description)
   - One for relationships (searchable by keywords + src + tgt + description)

2. **Knowledge Graph with Provenance**
   - Every node and edge tracks `source_id` (which chunks it came from)
   - This enables source attribution in answers

3. **Hybrid Query Strategy**
   - Low-level: Entity-centric retrieval → direct relationships
   - High-level: Relationship-centric retrieval → connected entities

4. **Multi-hop Path Finding**
   - Don't just return direct neighbors
   - Find paths up to 3 hops connecting query-relevant entities
   - Weight by frequency, prune by threshold

5. **Natural Language Path Descriptions**
   - Convert graph paths to human-readable text
   - Include entity types and descriptions for context

### 9.2 Minimal PathRAG Implementation

```python
class MinimalPathRAG:
    def __init__(self):
        self.entity_vdb = VectorDB()          # For entity search
        self.relation_vdb = VectorDB()        # For relationship search
        self.graph = nx.DiGraph()             # Knowledge graph
        self.chunks = {}                       # Source text storage

    def index(self, documents):
        # 1. Chunk documents
        chunks = chunk_documents(documents)

        # 2. Extract entities and relationships (LLM)
        for chunk in chunks:
            entities, relations = extract_kg(chunk)

            # 3. Update graph
            for entity in entities:
                self.graph.add_node(entity.name, **entity.data)
            for relation in relations:
                self.graph.add_edge(relation.src, relation.tgt, **relation.data)

            # 4. Index in vector DBs
            self.entity_vdb.add(entities)
            self.relation_vdb.add(relations)

    def query(self, question):
        # 1. Extract keywords
        hl_keywords, ll_keywords = extract_keywords(question)

        # 2. Entity retrieval (low-level)
        entities = self.entity_vdb.search(ll_keywords, top_k=40)

        # 3. Relationship retrieval (high-level)
        relations = self.relation_vdb.search(hl_keywords, top_k=40)

        # 4. PATH FINDING (the key innovation)
        entity_names = [e.name for e in entities]
        paths = find_all_paths(self.graph, entity_names, max_hops=3)
        weighted_paths = weight_paths(paths, threshold=0.3, alpha=0.8)
        path_descriptions = paths_to_text(weighted_paths, self.graph)

        # 5. Gather source texts
        sources = get_source_texts(entities, relations, self.chunks)

        # 6. Generate response
        context = format_context(entities, relations, path_descriptions, sources)
        return llm_generate(question, context)
```

### 9.3 Customization Points

| Component | How to Customize |
|-----------|------------------|
| **Entity Types** | Modify `PROMPTS["DEFAULT_ENTITY_TYPES"]` |
| **Extraction Prompt** | Edit `PROMPTS["entity_extraction"]` |
| **Path Parameters** | Adjust `threshold`, `alpha`, `max_hops` |
| **Storage Backend** | Implement `BaseKVStorage`, `BaseVectorStorage`, `BaseGraphStorage` |
| **LLM Provider** | Set `llm_model_name` to any LiteLLM-supported model (e.g. `gemini/gemini-2.5-flash`), or add a custom function in `llm.py` |
| **Embedding Model** | Set `embedding_model_name` and `embedding_dim` (e.g. `gemini/gemini-embedding-001`, 3072), or provide a custom `embedding_func` |

### 9.4 Performance Considerations

1. **Path finding is O(n^k)** where n=entities and k=max_hops
   - Limit `top_k` retrieval to control n
   - Cap at 3 hops (exponential growth)

2. **Vector DB choice matters**
   - NanoVectorDB: Good for <100k entities
   - Milvus/Chroma: Better for large scale

3. **LLM caching**
   - PathRAG caches LLM responses by query hash
   - Implement `embedding_cache_config` for similar query detection
   - **Remote backend caveat:** The cache stores all responses as a nested JSON dict keyed by `mode` (see `handle_cache` / `save_to_cache` in `utils.py`). On every cache read or write the entire dict must be fetched from the KV store, updated in memory, and written back. This read-modify-write pattern is efficient for the local `JsonKVStorage` (in-memory dict backed by a single JSON file), but causes unnecessary network round-trips and growing payload sizes with remote backends such as Spanner. When using a remote KV backend, set `enable_llm_cache=False` to avoid this overhead.

4. **Async everywhere**
   - All operations are async for parallelization
   - Use `limit_async_func_call()` to prevent rate limiting

---

## Summary

PathRAG's key innovation is the **relational path pruning algorithm** that:

1. Retrieves entities and relationships via dual vector search
2. Finds multi-hop paths (1-3 hops) between relevant entities
3. Weights paths by traversal frequency using BFS
4. Prunes weak connections using threshold filtering
5. Converts surviving paths to natural language descriptions

This provides richer context than standard RAG by surfacing **indirect semantic connections** that would otherwise be missed.

