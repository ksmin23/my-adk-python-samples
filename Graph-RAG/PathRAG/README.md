# PathRAG Agent with Spanner Graph

This project demonstrates how to implement a PathRAG (Path-based Retrieval Augmented Generation) agent using the Agent Development Kit (ADK) and Google Cloud Spanner as the backend storage for Knowledge Graph, Vector Store, and Key-Value Store.

It leverages the [PathRAG](https://github.com/BUPT-GAMMA/PathRAG) library, adapted to use Google Vertex AI (Gemini) models and Spanner storage.

## Project Structure

```
/PathRAG
├── pathrag_with_spanner/    # ADK Agent directory
│   ├── agent.py             # Agent definition
│   ├── prompt.py            # Agent system instructions
│   ├── tools.py             # Agent tools
│   └── test_pathrag_spanner.py # Test script
├── data_ingestion/          # Data ingestion directory
│   └── insert_document.py   # Script to ingest documents into Spanner
├── shared_lib/              # Shared libraries
│   ├── gemini_client.py     # Vertex AI Gemini wrapper
│   └── spanner_storage.py   # Spanner storage implementation
├── utils/                   # Utility scripts
│   └── create_spanner_db.py # Script to provision Spanner resources
└── requirements.txt         # Project dependencies
```

## Prerequisites

Before you begin, ensure you have an active Google Cloud project and the following tools installed:
-   [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
-   [uv](https://github.com/astral-sh/uv) (for Python package management)

### 1. Configure your Google Cloud project

Authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Set up your project and enable required APIs:

```bash
# Set your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Enable APIs
gcloud services enable \
  spanner.googleapis.com \
  aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 2. Create a Spanner Instance and Database

You can manually create the instance, or use the provided utility script later to create the database and schema.

```bash
export SPANNER_INSTANCE="pathrag-instance"
export SPANNER_DATABASE="pathrag-db"
export SPANNER_REGION="us-central1"

# Create Instance
gcloud spanner instances create $SPANNER_INSTANCE \
  --config=regional-$SPANNER_REGION \
  --description="PathRAG Instance" \
  --nodes=1 \
  --edition=ENTERPRISE
```

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Provision Spanner Resources

Run the utility script to create the necessary tables and Property Graph schema in Spanner.

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export SPANNER_INSTANCE="pathrag-instance"
export SPANNER_DATABASE="pathrag-db"

# Run provisioning script
python utils/create_spanner_db.py
```

### 3. Data Ingestion

Ingest documents into the PathRAG Knowledge Graph.

```bash
# Set additional env var for Gemini
export GOOGLE_GENAI_USE_VERTEXAI="1"
export GOOGLE_CLOUD_LOCATION="us-central1"

# Ingest a document
python data_ingestion/insert_document.py --file your_document.txt
```

## Run the Agent

You can run the agent utilizing the ADK CLI or the provided test script.

### Using ADK CLI (Web Interface)

```bash
# Ensure PYTHONPATH includes the current directory
export PYTHONPATH=$PYTHONPATH:.

# Run ADK Web Interface targeting the agent directory
adk web pathrag_with_spanner
```

### Using Test Script

```bash
python pathrag_with_spanner/test_pathrag_spanner.py
```

## Architecture

-   **LLM**: Vertex AI Gemini 2.5 Flash
-   **Storage**: Google Cloud Spanner
    -   `PathRagKV`: Key-Value store for metadata and caching.
    -   `PathRagVector`: Vector store for embeddings (Supports Spanner Vector Search).
    -   `PathRagGraph`: Property Graph (Nodes and Edges) for structural knowledge.
-   **Library**: Custom `SpannerPathRAG` implementation extending `PathRAG`.

## References

- [PathRAG GitHub](https://github.com/BUPT-GAMMA/PathRAG)
- [Google Cloud Spanner Graph](https://cloud.google.com/spanner/docs/graph/overview)
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/agent-engine/overview)
