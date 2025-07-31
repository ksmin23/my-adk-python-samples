# Google Agent Development Kit (ADK) - Python Samples

This repository contains a collection of sample agents built using the [Google Agent Development Kit (ADK)](https://developers.google.com/agent-development-kit). Each sample is a self-contained application demonstrating different use cases and integrations.

## General Prerequisites

-   [Python 3.x](https://www.python.org/)
-   [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
-   [Google Agent Development Kit (ADK)](https://developers.google.com/agent-development-kit/docs)

Please refer to the individual agent directories for specific dependencies and configuration steps.

## Available Agents

### 1. GCP Release Notes Agent

-   **Directory**: [`gcp-releasenotes-agent-app/`](./gcp-releasenotes-agent-app/)
-   **Description**: An agent designed to answer questions about Google Cloud release notes. It connects to a [MCP Toolbox for Databases](https://googleapis.github.io/genai-toolbox/getting-started/) service that queries a public BigQuery dataset.
-   **Features**:
    -   Demonstrates integration with a BigQuery-backed MCP Toolbox.
    -   Includes instructions for deploying the toolbox service to Cloud Run.

For detailed setup and execution instructions, please see the [GCP Release Notes Agent README](./gcp-releasenotes-agent-app/README.md).

### 2. Shop Search Agent

-   **Directory**: [`shop-agent-app/`](./shop-agent-app/)
-   **Description**: An agent that acts as a shopping assistant, using a tool to search for products in a catalog. It connects to a separate MCP server backed by Vertex AI Search for Retail.
-   **Features**:
    -   Illustrates how to connect an agent to a custom MCP server.
    -   Provides a clear example of a retail or e-commerce use case.

For detailed setup and execution instructions, please see the [Shop Search Agent README](./shop-agent-app/README.md).

### 3. Agentic RAG

This section includes agents that implement the Retrieval-Augmented Generation (RAG) pattern using different Google Cloud database services for vector search.

#### QnA Agent with AlloyDB

-   **Directory**: [`RAG/rag-with-alloydb/`](./RAG/rag-with-alloydb/)
-   **Description**: An agent that implements the RAG pattern using AlloyDB for PostgreSQL for vector search.
-   **Features**:
    -   Demonstrates using AlloyDB as a vector store for RAG.
    -   Includes data ingestion scripts for populating the vector database.
    -   Provides instructions for local execution and deployment to Vertex AI Agent Engine.

For detailed setup and execution instructions, please see the [RAG with AlloyDB Agent README](./RAG/rag-with-alloydb/README.md).

#### QnA Agent with BigQuery

-   **Directory**: [`RAG/rag-with-bigquery/`](./RAG/rag-with-bigquery/)
-   **Description**: An agent that implements the RAG pattern using BigQuery for vector search.
-   **Features**:
    -   Demonstrates using BigQuery as a vector store for RAG.
    -   Includes data ingestion scripts.
    -   Provides instructions for local execution and deployment to Vertex AI Agent Engine.

For detailed setup and execution instructions, please see the [RAG with BigQuery Agent README](./RAG/rag-with-bigquery/README.md).

#### QnA Agent with Spanner

-   **Directory**: [`RAG/rag-with-spanner/`](./RAG/rag-with-spanner/)
-   **Description**: An agent that implements the RAG pattern using Google Cloud Spanner for vector search.
-   **Features**:
    -   Demonstrates using Spanner as a vector store for RAG.
    -   Includes data ingestion scripts.
    -   Provides instructions for local execution and deployment to Vertex AI Agent Engine.

For detailed setup and execution instructions, please see the [RAG with Spanner Agent README](./RAG/rag-with-spanner/README.md).
