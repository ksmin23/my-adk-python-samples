# Dynamic MCP Agent with ADK

This project demonstrates an advanced agent built with the Google Agent Development Kit (ADK) that dynamically discovers and loads tools from Google Managed MCP servers. By only loading tools into the context when they are actually needed, this agent can support hundreds of tools while maintaining high performance and reducing token costs by over 90%.

## Overview

This agent is designed for scalability and efficiency. Instead of pre-loading a large set of tools, it uses a two-phase "Search & Load" pattern.

- **`mcp_servers_agents/`**: The main agent application.
  - **`agent.py`**: Defines the `root_agent` and implements the `after_tool_callback` for dynamic tool injection.
  - **`tools.py`**: Defines the `search_available_tools` and `load_tool` functions, and handles connections to Google Managed MCP servers (Maps, BigQuery).
  - **`registry.py`**: Implements a tool registry using the `rank_bm25` algorithm to index and search through all available MCP tools based on their descriptions.
  - **`requirements.txt`**: Project dependencies including `google-adk`, `rank_bm25`, and `google-auth`.

## Architecture

The agent uses a dynamic injection flow where the primary agent discovers tools using a lightweight search tool and then loads the full tool definition into its context.

```ascii
+----------+
|          |
|   User   |
|          |
+----------+
     |
     | 1. Request (e.g., "Find coffee shop statistics in BigQuery")
     v
+-------------------------------------------------------------+
| Google Cloud / Local Environment                            |
|                                                             |
|  +-------------------------------------------------------+  |
|  | ADK Agent (mcp_dynamic_agent)                         |  |
|  |                                                       |  |
|  |  [Turn 1]                                             |  |
|  |  - Calls `search_available_tools`                     |  |
|  |  - Finds "bigquery_query" in Registry                 |  |
|  |  - Calls `load_tool("bigquery_query")`                |  |
|  +-------------------------------------------------------+  |
|           |                       ^                         |
|           | 2. Search & Load      | 3. Tool Injection       |
|           v                       | (after_tool_callback)   |
|  +-------------------+    +------------------------------+  |
|  | Tool Registry     |    | Google Managed MCP Servers   |  |
|  | (BM25 Index)      |    | (Maps, BigQuery)             |  |
|  +-------------------+    +------------------------------+  |
|                               |                             |
|                               | 4. Execute Injected Tool    |
|                               v                             |
|                      +-----------------------+              |
|                      | Final Tool Output     |              |
|                      +-----------------------+              |
+-------------------------------------------------------------+
```

## Getting Started

### 1. Prerequisites

- Python 3.10+
- `uv` (or `pip` and `venv`)
- A Google Cloud Project with Billing enabled.

### 2. Installation

```bash
# Navigate to the project directory
cd dynamic-tool-search-tool/mcp_servers_agents

# Create and activate a virtual environment
uv venv
source .venv/bin/activate

# Install packages
uv pip install -r requirements.txt
```

### 3. Configuration

1.  **Environment Variables**:
    Create a `.env` file in the `mcp_servers_agents` directory:
    ```bash
    cp .env.example .env
    ```
2.  **Edit `.env`**:
    - `GOOGLE_CLOUD_PROJECT`: Your GCP Project ID.
    - `GOOGLE_MAPS_API_KEY`: A valid Google Maps API Key.
3.  **Authentication**:
    Ensure you have authenticated with your GCP account for BigQuery access:
    ```bash
    gcloud auth application-default login
    ```

## Running the Agent

You can interact with the agent locally using the ADK web interface.

1.  Navigate to the `dynamic-tool-search-tool` directory.
2.  Run the agent:
    ```bash
    adk web
    ```
3.  Open the provided URL (default `http://127.0.0.1:8000`) and select `mcp_servers_agents`.

## Deploying to Vertex AI Agent Engine

1.  **Authenticate**:
    ```bash
    gcloud auth login
    gcloud config set project your-gcp-project-id
    ```
2.  **Deploy**:
    ```bash
    adk deploy agent_engine dynamic-tool-search-tool/mcp_servers_agents \
      --staging_bucket="gs://your-staging-bucket" \
      --display_name="Dynamic MCP Agent" \
      --project="your-gcp-project-id" \
      --region="us-central1"
    ```

## Example Usage

**User:**
> "I want to find popular spots near Seoul Station and check for any interesting data in BigQuery datasets."

**Agent Workflow:**
1.  The agent calls `search_available_tools(query="popular spots near Seoul Station")`.
2.  The registry returns `search_places` from the Maps MCP.
3.  The agent calls `load_tool("search_places")`.
4.  The tool is injected. Now the agent calls `search_places(...)` to get the actual data.
5.  Repeats the process for BigQuery queries.

## References

- [ADK Documentation: Callbacks - Observe, Customize, and Control Agent Behavior](https://google.github.io/adk-docs/callbacks/)
- [Implementing Anthropic-style Dynamic Tool Search Tool](https://medium.com/google-cloud/implementing-anthropic-style-dynamic-tool-search-tool-f39d02a35139)
- [Tutorial: Getting Started with Google MCP Services](https://medium.com/google-cloud/tutorial-getting-started-with-google-mcp-services-60b23b22a0e7)
- [Google Cloud MCP Overview](https://docs.cloud.google.com/mcp/overview)
