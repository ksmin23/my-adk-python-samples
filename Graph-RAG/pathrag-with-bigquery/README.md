# PathRAG Agent with BigQuery Graph

This project demonstrates how to implement a PathRAG (Path-based Retrieval Augmented Generation) agent using the Agent Development Kit (ADK) with **Google Cloud BigQuery** as the storage backend.

It leverages the [PathRAG](https://github.com/ksmin23/PathRAG) library with the [pathrag-bigquery](https://github.com/ksmin23/pathrag-bigquery) storage plugin and LiteLLM for Gemini model integration.

## Architecture

<table border="0" cellpadding="0" cellspacing="0" style="border: none; border-collapse: collapse;">
  <tr style="border: none;">
    <td valign="middle" align="center" width="70%" style="border: none;">
      <img src="./assets/pathrag-framework-arch.png" alt="PathRAG Framework Architecture"><br><br>
      <em>Image Source: <a href="https://arxiv.org/abs/2502.14902">"PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths"</a></em>
    </td>
    <td valign="middle" width="30%" style="border: none;">
      <pre>User Query
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
    |-- Graph Search (BigQuery Property Graph)
    |-- Vector Search (BigQuery Vector Search)
    +-- Context assembly and return
    |
    v
ADK Agent generates final answer based on context</pre>
      <p><code>QueryParam(only_need_context=True)</code> skips answer generation inside PathRAG, letting the ADK Agent's LLM generate the final answer from the retrieved context.</p>
    </td>
  </tr>
</table>

## How It Works

1. **User sends a query** to the ADK Agent.
2. **Agent calls `pathrag_tool`** with the query.
3. **PathRAG processes the query**:
   - Extracts keywords (high-level & low-level) using LLM.
   - Searches the BigQuery Property Graph (entities, relationships, paths).
   - Searches the BigQuery Vector Store (semantic similarity).
   - Combines results into structured context.
4. **Context is returned** to the Agent (no LLM answer generation inside PathRAG).
5. **Agent generates the final answer** using the retrieved context.

## Project Structure

```
pathrag-with-bigquery/
├── pathrag_with_bigquery/            # ADK Agent directory
│   ├── __init__.py
│   ├── agent.py                     # ADK Agent definition (root_agent)
│   ├── prompt.py                    # Agent system instructions
│   ├── tools.py                     # pathrag_tool - context retrieval via PathRAG
│   └── .env.example                 # Environment variables template
├── data_ingestion/                  # Data ingestion directory
│   └── insert.py                    # Script to ingest documents
├── requirements.txt                 # Project dependencies
└── README.md
```

### Key Files

| File | Description |
|------|-------------|
| `pathrag_with_bigquery/agent.py` | `root_agent` definition using Gemini 2.5 Flash and `pathrag_tool` |
| `pathrag_with_bigquery/tools.py` | `pathrag_tool` function, extracts context from PathRAG |
| `pathrag_with_bigquery/prompt.py` | System instruction guiding the Agent to answer based on tool-retrieved context |
| `data_ingestion/insert.py` | Script to ingest documents into the PathRAG Knowledge Graph |

## Storage Backend

This project uses **Google Cloud BigQuery** for scalable, serverless storage. Tables and Property Graph are automatically created by `pathrag-bigquery` on first use via lazy initialization (`_ensure_schema()`).

| Component | Backend |
|-----------|---------|
| KV Storage | `BigQueryKVStorage` |
| Vector Storage | `BigQueryVectorDBStorage` |
| Graph Storage | `BigQueryGraphStorage` |

## Prerequisites

Before you begin, ensure you have the following tools installed:

- [uv](https://github.com/astral-sh/uv) (for Python package management)
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)

### 1. Configure your Google Cloud project

First, authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Next, set up your project and enable the necessary APIs:

```bash
export PROJECT_ID=$(gcloud config get-value project)

gcloud services enable \
  bigquery.googleapis.com \
  aiplatform.googleapis.com
```

### 2. Create a BigQuery Dataset

Create a BigQuery dataset using the `gcloud` CLI.

```bash
# Set environment variables
export BIGQUERY_PROJECT=$PROJECT_ID
export BIGQUERY_DATASET="pathrag"
export BIGQUERY_LOCATION="us-central1"

# Create the BigQuery dataset
bq --location=$BIGQUERY_LOCATION mk \
  --dataset \
  --description="PathRAG Dataset" \
  ${BIGQUERY_PROJECT}:${BIGQUERY_DATASET}
```

### 3. Set Environment Variables

Copy the example file and edit it:

```bash
cp pathrag_with_bigquery/.env.example pathrag_with_bigquery/.env
```

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="1"
export BIGQUERY_PROJECT="your-project-id"
export BIGQUERY_DATASET="pathrag"
```

## Setup

### 1. Install Dependencies

This project uses `uv` to manage the Python virtual environment and package dependencies.

**Create and activate the virtual environment:**

```bash
# Create the virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate
```

**Install dependencies:**

```bash
uv pip install -r requirements.txt
```

### 2. Data Ingestion

First, load the environment variables from the `.env` file:

```bash
source pathrag_with_bigquery/.env
```

Ingest documents into the PathRAG Knowledge Graph.

```bash
# Ingest sample documents (Apple, Steve Jobs, Google)
python data_ingestion/insert.py --sample

# Or ingest your own document
python data_ingestion/insert.py --file your_document.txt
```

### 3. Run the Agent

You can run the agent using either the command-line interface or a web-based interface.

#### Using the Command-Line Interface (CLI)

```bash
adk run pathrag_with_bigquery
```

#### Using the Web Interface

```bash
adk web
```

## References

- :octocat: [PathRAG GitHub](https://github.com/ksmin23/PathRAG): Knowledge Graph-based RAG system that uses path-based retrieval through knowledge graphs for more accurate, explainable, and context-aware LLM responses.
- :octocat: [pathrag-bigquery GitHub](https://github.com/ksmin23/pathrag-bigquery): Google Cloud BigQuery storage backend for PathRAG.
- [Intro to GraphRAG](https://graphrag.com/concepts/intro-to-graphrag/) - A dive into GraphRAG pattern details
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- **BigQuery Graph**
  - [Introduction to BigQuery Graph](https://docs.cloud.google.com/bigquery/docs/graph-overview)
  - [The Practical Guide to BigQuery Graph: Resources, Codelabs, and GQL Examples](https://medium.com/google-cloud/the-practical-guide-to-bigquery-graph-resources-codelabs-and-gql-examples-c88e8ed67a54)
- [Vertex AI Gemini](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini)
