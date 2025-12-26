# Google Agent Development Kit (ADK) - Python Samples

This repository contains a collection of sample agents built using the [Google Agent Development Kit (ADK)](https://developers.google.com/agent-development-kit). Each sample is a self-contained application demonstrating different use cases and integrations.

## Table of Contents

- [General Prerequisites](#general-prerequisites)
- [Available Agents](#available-agents)
  - [1. GCP Release Notes Agent](#1-gcp-release-notes-agent)
  - [2. Shop Search Agent](#2-shop-search-agent)
  - [3. Restaurant Finder Agent](#3-restaurant-finder-agent)
  - [4. Shopper's Concierge Agent](#4-shoppers-concierge-agent)
  - [5. Agentic RAG](#5-agentic-rag)
    - [QnA Agent with AlloyDB](#qna-agent-with-alloydb)
    - [QnA Agent with BigQuery](#qna-agent-with-bigquery)
    - [QnA Agent with Spanner](#qna-agent-with-spanner)
    - [More RAG Agents](#more-rag-agents)
  - [6. Graph RAG](#6-graph-rag)
    - [Graph RAG with Spanner](#graph-rag-with-spanner)
  - [7. ADK BigQuery Logging Plugin Example](#7-adk-bigquery-logging-plugin-example)
  - [8. Agent Memory](#8-agent-memory)
    - [ADK Redis Session Service](#adk-redis-session-service)
    - [ADK Redis Memory Service](#adk-redis-memory-service)
  - [9. Dynamic MCP Agent](#9-dynamic-mcp-agent)
- [References](#references)

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

### 3. Restaurant Finder Agent

-   **Directory**: [`restaurant-finder/`](./restaurant-finder/)
-   **Description**: A conversational AI agent that helps users find restaurants based on a specific dish or ingredient, leveraging the Google Maps Platform API.
-   **Features**:
    -   Demonstrates how an agent can use external tools (Google Maps API) to answer user queries.
    -   Provides real-time restaurant information.

For detailed setup and execution instructions, please see the [Restaurant Finder Agent README](./restaurant-finder/README.md).

### 4. Shopper's Concierge Agent

-   **Directory**: [`shopper-concierge-demo/`](./shopper-concierge-demo/)
-   **Description**: An advanced shopping assistant that uses a sub-agent for research to provide more relevant product recommendations.
-   **Features**:
    -   Showcases a multi-agent architecture where a primary agent delegates tasks to a specialized sub-agent.
    -   Includes a Gradio web interface for a complete user experience.

For detailed setup and execution instructions, please see the [Shopper's Concierge Agent README](./shopper-concierge-demo/README.md).

### 5. Agentic RAG

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

#### More RAG Agents

This repository contains additional RAG agent implementations that demonstrate integration with various Google Cloud services. Below is a list of other available RAG agents:

-   **RAG Engine with Managed DB**:
    -   **Directory**: [`RAG/rag-engine-with-managed-db/`](./RAG/rag-engine-with-managed-db/)
    -   **Description**: An agent that leverages the managed Vertex AI RAG Engine with its own fully managed database, eliminating the need to manage a separate Vector Search index.
    -   **README**: [RAG Engine with Managed DB README](./RAG/rag-engine-with-managed-db/README.md)

-   **RAG Engine with Vector Search**:
    -   **Directory**: [`RAG/rag-engine-with-vectorsearch/`](./RAG/rag-engine-with-vectorsearch/)
    -   **Description**: An agent that uses the managed Vertex AI RAG Engine with a Vertex AI Vector Search index as its backend for efficient, scalable document retrieval.
    -   **README**: [RAG Engine with Vector Search README](./RAG/rag-engine-with-vectorsearch/README.md)

-   **RAG with Vector Search and Datastore**:
    -   **Directory**: [`RAG/rag-with-vectorsearch-ds/`](./RAG/rag-with-vectorsearch-ds/)
    -   **Description**: An agent that uses Vertex AI Vector Search as the vector store and Firestore in Datastore mode as the document store.
    -   **README**: [RAG with Vector Search and Datastore README](./RAG/rag-with-vectorsearch-ds/README.md)

-   **RAG with Vector Search and GCS**:
    -   **Directory**: [`RAG/rag-with-vectorsearch-gcs/`](./RAG/rag-with-vectorsearch-gcs/)
    -   **Description**: An agent that uses Vertex AI Vector Search as the vector store and Google Cloud Storage (GCS) as the document store.
    -   **README**: [RAG with Vector Search and GCS README](./RAG/rag-with-vectorsearch-gcs/README.md)

### 6. Graph RAG

This section includes agents that implement the Graph Retrieval-Augmented Generation (Graph RAG) pattern.

#### Graph RAG with Spanner

-   **Directory**: [`Graph-RAG/graph-rag-with-spanner/`](./Graph-RAG/graph-rag-with-spanner/)
-   **Description**: An agent that implements the Graph RAG pattern using Google Cloud Spanner Graph for knowledge graph storage and retrieval.
-   **Features**:
    -   Demonstrates using Spanner Graph as a knowledge graph store.
    -   Includes data ingestion scripts using `LLMGraphTransformer` to extract nodes and relationships from documents.
    -   Leverages concise retrieval using `SpannerGraphStore`.
-   **README**: [Graph RAG with Spanner README](./Graph-RAG/graph-rag-with-spanner/README.md)

### 7. ADK BigQuery Logging Plugin Example

-   **Directory**: [`plugins/bigquery-logging-plugin/`](./plugins/bigquery-logging-plugin/)
-   **Description**: A sample agent demonstrating how to use the `BigQueryAgentAnalyticsPlugin` to log agent interactions and analytics to Google BigQuery. This enables monitoring agent performance, debugging issues, and gaining insights into user interactions.
-   **Features**:
    -   Captures events such as tool calls, agent responses, and errors.
    -   Stores analytics data in a structured BigQuery table.

For detailed setup and execution instructions, please see the [ADK BigQuery Logging Plugin Example README](./plugins/bigquery-logging-plugin/README.md).

### 8. Agent Memory

This section includes agents that demonstrate how to manage agent memory and session state.

#### ADK Redis Session Service

-   **Directory**: [`agent-memory/redis-session-service/`](./agent-memory/redis-session-service/)
-   **Description**: An agent that demonstrates how to use Redis for session state management, allowing for scalable and persistent user sessions.
-   **Features**:
    -   Integrates a custom session service with ADK.
    -   Persists conversation state in a Redis database.
    -   Includes instructions for local execution and deployment to Cloud Run.

For detailed setup and execution instructions, please see the [ADK Redis Session Service README](./agent-memory/redis-session-service/README.md).

#### ADK Redis Memory Service

-   **Directory**: [`agent-memory/redis-memory-service/`](./agent-memory/redis-memory-service/)
-   **Description**: An agent demonstrating a custom long-term memory service using Redis. It leverages Redis's Vector Search for searchable, personalized memories, enhancing continuity across user conversations.
-   **Features**:
    -   Demonstrates implementing a custom long-term memory service using Redis.
    -   Leverages Redis's Vector Search for searchable, long-term knowledge storage.
    -   Enhances personalization and continuity across user conversations.

For detailed setup and execution instructions, please see the [ADK Redis Memory Service README](./agent-memory/redis-memory-service/README.md).

### 9. Dynamic MCP Agent

-   **Directory**: [`dynamic-tool-search-tool/`](./dynamic-tool-search-tool/)
-   **Description**: An advanced agent that demonstrates dynamic discovery and loading of tools from Google Managed MCP servers. It uses a "Search & Load" pattern to support vast tool libraries efficiently.
-   **Features**:
    -   Dynamic tool injection via the `after_tool_callback` mechanism.
    -   High scalability, supporting hundreds of tools with minimal overhead.
    -   Uses BM25 search to find relevant tools based on user intent.

For detailed setup and execution instructions, please see the [Dynamic MCP Agent README](./dynamic-tool-search-tool/README.md).

## References

-   [ADK Official Docs](https://google.github.io/adk-docs/)
    -   [ADK Python Repository](https://github.com/google/adk-python)
-   [ADK Python Community Contributions](https://github.com/google/adk-python-community)
-   [ADK Samples Repo](https://github.com/google/adk-samples)
-   [Agentic Design Patterns](https://docs.google.com/document/d/1rsaK53T3Lg5KoGwvf8ukOUvbELRtH-V0LnOIFDxBryE/preview?tab=t.0#heading=h.pxcur8v2qagu)
-   [ADK Web Book by Amulya Bhatia](https://iamulya.one/tags/agent-development-kit/)
