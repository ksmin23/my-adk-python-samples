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
