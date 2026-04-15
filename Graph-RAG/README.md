# Graph RAG (Graph-based Retrieval-Augmented Generation) Samples

This directory contains a collection of sample projects demonstrating various Graph-based Retrieval-Augmented Generation (Graph RAG) architectures using the Google Agent Development Kit (ADK) and different Google Cloud services for graph and vector storage.

## Projects

Here is a list of the available Graph RAG sample projects:

### 1. Naive Graph RAG

These samples demonstrate direct implementation of Graph RAG patterns using Google Cloud's graph database capabilities.

-   **[Agentic Graph RAG with Spanner Graph](./graph-rag-with-spanner/)**
    -   **Description**: A sample implementation of an Agentic Graph RAG using Spanner Graph, demonstrating data ingestion and agent orchestration.
    -   **Storage Backend**: Cloud Spanner (Spanner Graph).

### 2. LightRAG Implementations

These samples leverage the LightRAG framework, which incorporates graph structures into text indexing and retrieval processes.

-   **[LightRAG with BigQuery](./lightrag-with-bigquery/)**
    -   **Description**: Implements a LightRAG agent using BigQuery as the storage backend (KV, Vector, and Graph storage).
    -   **Storage Backend**: Google Cloud BigQuery.

-   **[LightRAG with Spanner](./lightrag-with-spanner/)**
    -   **Description**: Implements a LightRAG agent using Google Cloud Spanner as the storage backend.
    -   **Storage Backend**: Cloud Spanner.

### 3. PathRAG Implementations

These samples leverage the PathRAG framework, an advanced approach that combines knowledge graphs with LLMs using relational paths for more accurate and explainable responses.

-   **[PathRAG with BigQuery](./pathrag-with-bigquery/)**
    -   **Description**: Implements a PathRAG agent using BigQuery as the storage backend.
    -   **Storage Backend**: Google Cloud BigQuery.

-   **[PathRAG with Spanner](./pathrag-with-spanner/)**
    -   **Description**: Implements a PathRAG agent using Cloud Spanner as the storage backend.
    -   **Storage Backend**: Cloud Spanner.
