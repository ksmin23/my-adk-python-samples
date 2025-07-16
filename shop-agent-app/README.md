# Shop Search Agent

This agent acts as a shopping assistant, using a tool to search for products in a product catalog.

## Overview

The agent is built using the Google Agent Development Kit (ADK). It leverages the Model Context Protocol (MCP) to communicate with a separate server process that provides access to a Vertex AI Search for Retail backend.

The core logic is in `shop_agent/agent.py`. It defines an `LlmAgent` that is configured to use the `search_products` tool, which is made available through an `MCPToolset`. The toolset communicates with a separate MCP server, which you can find at [mcp-vertex-ai-retail-search-server](https://github.com/ksmin23/mcp-vertex-ai-retail-search-server).

## Prerequisites

1.  **Set Up and Run the MCP Server:** This agent requires the `mcp-vertex-ai-retail-search-server` to be running.
    *   First, clone the server repository to a separate location:
        ```bash
        git clone https://github.com/ksmin23/mcp-vertex-ai-retail-search-server.git
        ```
    *   Follow the setup instructions in the cloned repository's `README.md`. The key steps are:
        *   Installing its dependencies.
        *   Creating and configuring a `.env` file with your project details (`PROJECT_ID`, `LOCATION`, etc.).
        *   Starting the server. **Make a note of the URL where the server is running** (e.g., `http://localhost:8000/mcp/`).

2.  **Install Agent Dependencies:**
    *   Navigate to this agent's directory from the repository root:
        ```bash
        cd shop-agent-app
        ```
    *   Create a virtual environment using `uv`:
        ```bash
        uv venv
        ```
    *   Activate the virtual environment:
        *   **macOS/Linux:**
            ```bash
            source .venv/bin/activate
            ```
        *   **Windows:**
            ```bash
            .venv\Scripts\activate
            ```
    *   Install the required Python packages:
        ```bash
        uv pip install -r shop_agent/requirements.txt
        ```

3.  **Configure Agent Connection:**
    *   Create a `.env` file for the agent by copying the example:
        ```bash
        # Ensure you are in the shop-agent-app/ directory
        cp shop_agent/.env.example shop_agent/.env
        ```
    *   Edit the `shop_agent/.env` file and set `MCP_SERVER_URL` to the URL of the MCP server from step 1.

## Running the Agent Locally

You can run this agent using the ADK Web UI for interactive testing.

1.  **Start the ADK Web Server:** From the `shop-agent-app/` directory, run the following command:
    ```bash
    adk web
    ```
2.  **Interact with the Agent:** Open the provided URL in your browser and select the `shop_agent` from the list of available agents.

## Deploying to Cloud Run

You can deploy this agent as a containerized application on Google Cloud Run.

### Using the ADK CLI (Recommended)

Using the `adk` command-line tool is the simplest way to deploy.

1.  **Authenticate with Google Cloud**:
    First, run the following command to authenticate:
    ```bash
    gcloud auth login
    ```

2.  **Set Project and Location**:
    To simplify deployment, you can set the following environment variables.
    ```bash
    # Ensure these are set correctly for your environment
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    ```

3.  **Deploy**:
    From the `shop-agent-app/` directory, run the following command to deploy the agent:
    ```bash
    adk deploy cloud_run \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name="shop-agent-service" \
        --app_name="shop-agent-app" \
        --with_ui \
        ./shop_agent
    ```
    During deployment, you may be prompted to allow unauthenticated invocations for the service. The ADK automatically handles containerization and deployment. Once complete, it will provide a URL to access your agent on Cloud Run.


## Example Usage

Once the agent is running in the ADK Web UI, you can interact with it.

**Example prompt:**
> "Can you find me some hoodies?"

The agent will use the `search_products` tool to query the catalog and return the results.

![](./assets/shop-agent-01.png)
![](./assets/shop-agent-02.png)

## References

- [(YouTube) Build AI agents for e-commerce with ADK + Vector Search](https://www.youtube.com/watch?v=UIntXBP--gI)
- [Agent Development Kit (ADK)](https://goo.gle/3RGrB9T)
- [Vertex AI Vector Search](https://goo.gle/3T5xxK5)
- [Shopper's Concierge demo video](https://goo.gle/4jRbMJb)
- [Shopper's Concierge sample notebook](https://goo.gle/4kMkxot)