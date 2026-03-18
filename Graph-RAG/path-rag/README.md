# PathRAG Agent with Spanner Graph

This project demonstrates how to implement a PathRAG (Path-based Retrieval Augmented Generation) agent using the Agent Development Kit (ADK) and Google Cloud Spanner as the backend storage for Knowledge Graph, Vector Store, and Key-Value Store.

It leverages the [PathRAG](https://github.com/BUPT-GAMMA/PathRAG) library with built-in Spanner storage backends and LiteLLM for Gemini model integration.

## Architecture

```
User Query
    |
    v
ADK Agent (Gemini 2.5 Flash)
    |  tool call
    v
pathrag_tool(query)
    |
    v
PathRAG.aquery(only_need_context=True)
    |-- Keyword Extraction (LLM)
    |-- Graph Search (Spanner Property Graph)
    |-- Vector Search (Spanner Vector Search)
    +-- Context assembly and return
    |
    v
ADK Agent generates final answer based on context
```

`QueryParam(only_need_context=True)` skips answer generation inside PathRAG, letting the ADK Agent's LLM generate the final answer from the retrieved context.

## How It Works

1. **User sends a query** to the ADK Agent.
2. **Agent calls `pathrag_tool`** with the query.
3. **PathRAG processes the query**:
   - Extracts keywords (high-level & low-level) using LLM.
   - Searches the Spanner Graph (entities, relationships, paths).
   - Searches the Spanner Vector Store (semantic similarity).
   - Combines results into structured context.
4. **Context is returned** to the Agent (no LLM answer generation inside PathRAG).
5. **Agent generates the final answer** using the retrieved context.

## :file_folder: Project Structure

```
path-rag/
|-- pathrag_with_spanner/         # ADK Agent directory
|   |-- __init__.py
|   |-- agent.py                  # ADK Agent definition (root_agent)
|   |-- prompt.py                 # Agent system instructions
|   |-- tools.py                  # pathrag_tool - context retrieval via PathRAG
|   +-- test_pathrag_spanner.py   # Test script using ADK Runner
|-- data_ingestion/               # Data ingestion directory
|   +-- insert_document.py        # Script to ingest documents into Spanner
+-- requirements.txt              # Project dependencies
```

### Key Files

| File | Description |
|------|-------------|
| `pathrag_with_spanner/agent.py` | `root_agent` definition using Gemini 2.5 Flash and `pathrag_tool` |
| `pathrag_with_spanner/tools.py` | `pathrag_tool` defined with `@tool` decorator, extracts context from PathRAG |
| `pathrag_with_spanner/prompt.py` | System instruction guiding the Agent to answer based on tool-retrieved context |
| `pathrag_with_spanner/test_pathrag_spanner.py` | Test script using ADK `Runner` + `InMemorySessionService` |
| `data_ingestion/insert_document.py` | Script to ingest documents into the PathRAG Knowledge Graph |

## :floppy_disk: Storage (Google Cloud Spanner)

Tables and Property Graph are automatically created by PathRAG's `_ensure_schema()` on first use.

**KV Storage** (`SpannerKVStorage`) — `{namespace}_kv`

| Table | Purpose |
|-------|---------|
| `full_docs_kv` | Full document storage |
| `text_chunks_kv` | Text chunk storage |
| `llm_response_cache_kv` | LLM response caching |

**Vector Storage** (`SpannerVectorDBStorage`) — `vdb_{namespace}`

| Table | Purpose |
|-------|---------|
| `vdb_entities` | Entity embeddings |
| `vdb_relationships` | Relationship embeddings |
| `vdb_chunks` | Chunk embeddings |

**Graph Storage** (`SpannerGraphStorage`) — `{namespace}_nodes`, `{namespace}_edges`

| Table | Purpose |
|-------|---------|
| `chunk_entity_relation_nodes` | Knowledge Graph nodes (entities) |
| `chunk_entity_relation_edges` | Knowledge Graph edges (relationships) |
| `pathrag_chunk_entity_relation` | Spanner Property Graph |

## Prerequisites

Before you begin, ensure you have an active Google Cloud project and the following tools installed:
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [uv](https://github.com/astral-sh/uv) (for Python package management)

### 1. Configure your Google Cloud project

Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Set up your project and enable required APIs:

```bash
export PROJECT_ID=$(gcloud config get-value project)

gcloud services enable \
  spanner.googleapis.com \
  aiplatform.googleapis.com
```

### 2. Create a Spanner Instance

```bash
export SPANNER_INSTANCE="pathrag-instance"
export SPANNER_DATABASE="pathrag-db"
export SPANNER_REGION="us-central1"

gcloud spanner instances create $SPANNER_INSTANCE \
  --config=regional-$SPANNER_REGION \
  --description="PathRAG Instance" \
  --nodes=1 \
  --edition=ENTERPRISE
```

### 3. Set Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="1"
export SPANNER_INSTANCE="pathrag-instance"
export SPANNER_DATABASE="pathrag-db"
```

## :rocket: Setup

### 1. Install Dependencies

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Data Ingestion

Ingest documents into the PathRAG Knowledge Graph.

```bash
python data_ingestion/insert_document.py --file your_document.txt
```

## :robot: Run the Agent

### Using ADK CLI (Web Interface)

```bash
adk web pathrag_with_spanner
```

## References

- :octocat: [PathRAG GitHub](https://github.com/ksmin23/PathRAG)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Google Cloud Spanner Graph](https://cloud.google.com/spanner/docs/graph/overview)
- [Vertex AI Gemini](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini)
