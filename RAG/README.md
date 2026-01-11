# RAG (Retrieval-Augmented Generation) Samples

This directory contains a collection of sample projects demonstrating various Retrieval-Augmented Generation (RAG) architectures using the Google Agent Development Kit (ADK) and different Google Cloud services for vector storage and retrieval.

## Projects

Here is a list of the available RAG sample projects:

### 1. Using Vertex AI RAG Engine

These samples leverage the fully managed Vertex AI RAG Engine, which simplifies the retrieval process.

-   **[RAG Engine with Managed DB](./rag-engine-with-managed-db/)**
    -   **Description**: Implements an Agentic RAG application using the Vertex AI RAG Engine with its own fully managed database. This is the simplest approach, as it doesn't require managing a separate Vector Search index.
    -   **Vector Store**: Vertex AI RAG Engine's Managed Database.

-   **[RAG Engine with Vector Search](./rag-engine-with-vectorsearch/)**
    -   **Description**: Implements an Agentic RAG application using the Vertex AI RAG Engine backed by a Vertex AI Vector Search index for efficient, scalable document retrieval.
    -   **Vector Store**: Vertex AI Vector Search.

### 2. Using Managed Databases with Vector Search Capabilities

These samples demonstrate how to build RAG applications by integrating directly with Google Cloud's managed databases that support vector search.

-   **[RAG with AlloyDB](./rag-with-alloydb/)**
    -   **Description**: An Agentic RAG implementation using the vector search feature of AlloyDB for PostgreSQL.
    -   **Vector Store**: AlloyDB for PostgreSQL.

-   **[RAG with BigQuery](./rag-with-bigquery/)**
    -   **Description**: An Agentic RAG implementation using BigQuery Vector Search.
    -   **Vector Store**: BigQuery.

-   **[RAG with Spanner](./rag-with-spanner/)**
    -   **Description**: An Agentic RAG implementation using the vector search feature of Google Cloud Spanner.
    -   **Vector Store**: Cloud Spanner.

### 3. Using Vertex AI Vector Search with a Separate Document Store

These samples showcase an architecture where Vertex AI Vector Search is used as a dedicated vector store for similarity searches, while a separate database or storage service holds the original documents.

-   **[RAG with Vector Search and Datastore](./rag-with-vectorsearch-ds/)**
    -   **Description**: An Agentic RAG implementation using Vertex AI Vector Search for vector retrieval and Firestore in Datastore mode as the document store.
    -   **Vector Store**: Vertex AI Vector Search.
    -   **Document Store**: Firestore (Datastore mode).

-   **[RAG with Vector Search and GCS](./rag-with-vectorsearch-gcs/)**
    -   **Description**: An Agentic RAG implementation using Vertex AI Vector Search for vector retrieval and Google Cloud Storage (GCS) as the document store.
    -   **Vector Store**: Vertex AI Vector Search.
    -   **Document Store**: Google Cloud Storage.

### 4. Using Vertex AI Vector Search 2.0 (Unified Vector Store)

These samples demonstrate the new capabilities of Vector Search 2.0, which supports storing both embeddings and data together, eliminating the need for a separate document store.

-   **[RAG with Vector Search 2.0](./rag-with-vectorsearch-2.0/)**
    -   **Description**: An Agentic RAG implementation using **Vertex AI Vector Search 2.0**. Features unified data storage, auto-embeddings, and hybrid search (Semantic + Keyword) with RRF ranking.
    -   **Vector Store**: Vertex AI Vector Search 2.0 (Unified).
