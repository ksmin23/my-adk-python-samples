# Shop Search Agent

This agent acts as a shopping assistant, using a tool to search a product catalog.

## Overview

This agent is built using the Google Agent Development Kit (ADK). It leverages the Model Context Protocol (MCP) to communicate with a separate server process that provides access to a Vertex AI Search for Commerce backend.

The core logic resides in `shop_agent/agent.py`. It defines an `LlmAgent` configured to use the `search_products` tool, which is made available through an `MCPToolset`. The toolset communicates with a separate MCP server, which can be found at [mcp-vertex-ai-retail-search-server](https://github.com/ksmin23/mcp-vertex-ai-retail-search-server).

## Architecture

This agent uses a secure, two-tiered network architecture within a Google Cloud VPC. The user-facing `Shop Search Agent` (`Cloud Run - A`) resides in a public subnet, while the backend `Vertex AI Search for Commerce MCP Server` (`Cloud Run - B`) is isolated in a private subnet. All communication between the two services occurs over the private VPC network.

```ascii
+----------+
|          |
|   User   |
|          |
+----------+
     |
     | 1. User Question (HTTPS)
     v
+-------------------------------------------------------------------+
| Google Cloud                                                      |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  | VPC                                                         |  |
|  |                                                             |  |
|  |  +-------------------------------------------------------+  |  |
|  |  | Public Subnet                                         |  |  |
|  |  |                                                       |  |  |
|  |  |    +--------------------------------+                 |  |  |
|  |  |    |    Shop Search Agent           |                 |  |  |
|  |  |    |    (Cloud Run - A)             |                 |  |  |
|  |  |    |    (Public Ingress)            |                 |  |  |
|  |  |    +--------------------------------+                 |  |  |
|  |  |                 |                                     |  |  |
|  |  +-----------------|-------------------------------------+  |  |
|  |                    | 2. MCP Call (Internal VPC)             |  |
|  |  +-----------------v-------------------------------------+  |  |
|  |  | Private Subnet                                        |  |  |
|  |  |                                                       |  |  |
|  |  |    +--------------------------------------------+     |  |  |
|  |  |    | Vertex AI Search for Commerce MCP Server   |     |  |  |
|  |  |    | (Cloud Run - B)                            |     |  |  |
|  |  |    | (Internal Ingress)                         |     |  |  |
|  |  |    +--------------------------------------------+     |  |  |
|  |  |                                                       |  |  |
|  |  +-------------------------------------------------------+  |  |
|  |                                                             |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
+-------------------------------------------------------------------+
```

### Diagram Description

1.  **Two-Tier Subnet Design**:
    *   The `Shop Search Agent (Cloud Run - A)` is deployed in a **Public Subnet**. It is configured with **Public Ingress** to receive requests from users over the internet.
    *   The `Vertex AI Search for Commerce MCP Server (Cloud Run - B)` is deployed in a **Private Subnet** with **Internal Ingress** only. This isolates it from the public internet.

2.  **Communication Path**:
    *   When a user sends a request to the agent (`Cloud Run - A`), the agent processes it and makes a call to the MCP server (`Cloud Run - B`).
    *   This call is routed internally through the VPC's private network. It does not traverse the public internet, ensuring secure and low-latency communication. No VPC Egress connector is required because both services are within the same VPC.

3.  **Architecture Purpose**:
    *   This architecture enhances security by exposing only the necessary web-facing component (`Cloud Run - A`) to the internet, while protecting the backend data-processing service (`Cloud Run - B`) in an isolated private network.

## Prerequisites

**Install Agent Dependencies:**
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

## Running the Agent Locally

1.  **Set Up and Run the MCP Server:** This agent requires the `mcp-vertex-ai-retail-search-server` to be running.
    *   First, clone the server repository to a separate location:
        ```bash
        git clone https://github.com/ksmin23/mcp-vertex-ai-retail-search-server.git
        ```
    *   Follow the setup instructions in the cloned repository's `README.md`. The key steps are:
        *   Installing its dependencies.
        *   Creating and configuring a `.env` file with your project details (`PROJECT_ID`, `LOCATION`, etc.).
        *   Starting the server. **Make a note of the URL where the server is running** (e.g., `http://localhost:8000/mcp/`).

2. **Configure Agent Connection:**
    *   Create a `.env` file for the agent by copying the example:
        ```bash
        # Ensure you are in the shop-agent-app/ directory
        cp shop_agent/.env.example shop_agent/.env
        ```
    *   Edit the `shop_agent/.env` file and set `MCP_SERVER_URL` to the URL of the running MCP server from step 1.

You can run this agent using the ADK Web UI for interactive testing.

1.  **Start the ADK Web Server:** From the `shop-agent-app/` directory, run the following command:
    ```bash
    adk web
    ```
2.  **Interact with the Agent:** Open the provided URL in your browser and select `shop_agent` from the list of available agents.

## Deploying to Cloud Run

You can deploy this agent as a containerized application on Google Cloud Run.

### **Deploy MCP Server to Cloud Run**:

This agent requires the `mcp-vertex-ai-retail-search-server` to be running on Cloud Run.
Follow the setup instructions in the cloned MCP server repository's `README.md`.
Ensure that the MCP server is deployed securely within a private VPC subnet.

**Make a note of the URL where the server is running** (e.g., `https://internal-mcp-vaisr-server-xxxxxxxx-uc.a.run.app/mcp/`).

### Using the ADK CLI (Recommended)

The [`deploy_to_cloud_run.py`](../deploy_to_cloud_run.py) tool provides the simplest way to deploy.

1.  **Authenticate with Google Cloud**:
    First, run the following command to authenticate:
    ```bash
    gcloud auth login
    ```

2.  **Set Project and Location**:
    To simplify deployment, you can set the following environment variables:
    ```bash
    # Ensure these are set correctly for your environment
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    ```

3.  **Deploy**:
    From the project root directory, run the following command to deploy the agent:
    ```bash
    python deploy_to_cloud_run.py --agent-folder=shop-agent-app/shop_agent \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name="shop-agent-service" \
        --vpc-egress="all-traffic" \
        --network=[VPC] \
        --subnet=[SUBNET] \
        --with-ui
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