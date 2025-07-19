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

## Getting Started

### 1. Prerequisites

First, install the agent's dependencies.

*   Navigate to this agent's directory from the repository root:
    ```bash
    cd shop-agent-app
    ```
*   Create and activate a virtual environment:
    ```bash
    # Create the virtual environment
    uv venv

    # Activate it (macOS/Linux)
    source .venv/bin/activate

    # Windows
    # .venv\Scripts\activate
    ```
*   Install the required Python packages:
    ```bash
    uv pip install -r shop_agent/requirements.txt
    ```

### 2. Running Locally

To run the agent locally, you must first run its required backend service, the `mcp-vertex-ai-retail-search-server`.

1.  **Run the MCP Server (Backend)**:
    *   In a separate terminal, clone and run the MCP server:
        ```bash
        git clone https://github.com/ksmin23/mcp-vertex-ai-retail-search-server.git
        cd mcp-vertex-ai-retail-search-server
        # Follow the setup instructions in that repository's README.md
        ```
    *   Once the server is running, **note the URL where it is being served** (e.g., `http://localhost:8000/mcp/`).

2.  **Configure and Run the Agent (Frontend)**:
    *   Return to the `shop-agent-app` directory.
    *   Create a `.env` file by copying the example:
        ```bash
        cp shop_agent/.env.example shop_agent/.env
        ```
    *   Edit `shop_agent/.env` and set `MCP_SERVER_URL` to the URL of your running MCP server.
    *   Start the ADK web server to interact with the agent:
        ```bash
        adk web
        ```
    *   Open the provided URL in your browser and select `shop_agent`.

### 3. Deploying to Cloud Run

You can deploy both the agent and its backend MCP server to Cloud Run for a scalable, production-ready setup.

1.  **Deploy the MCP Server (Backend)**:
    *   First, follow the deployment instructions in the [mcp-vertex-ai-retail-search-server repository](https://github.com/ksmin23/mcp-vertex-ai-retail-search-server).
    *   Ensure it is deployed with **internal ingress** within a private VPC subnet.
    *   Once deployed, **note its internal service URL**.

2.  **Deploy the Shop Agent (Frontend)**:
    *   **Authenticate with Google Cloud**:
        ```bash
        gcloud auth login
        ```
    *   **Set Environment Variables**:
        ```bash
        export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
        export GOOGLE_CLOUD_LOCATION="us-central1"
        # Set these to your specific VPC and Subnet names
        export VPC_NETWORK="your-vpc-network"
        export VPC_SUBNET="your-public-subnet"
        ```
    *   **Run the Deployment Script**:
        From the project root directory (`./my-adk-python-samples`), run the following command. The script handles containerization and deployment.
        ```bash
        python deploy_to_cloud_run.py --agent-folder=shop-agent-app/shop_agent \
            --project=$GOOGLE_CLOUD_PROJECT \
            --region=$GOOGLE_CLOUD_LOCATION \
            --service_name="shop-agent-service" \
            --vpc-egress="all-traffic" \
            --network=$VPC_NETWORK \
            --subnet=$VPC_SUBNET \
            --with-ui
        ```
    *   The `--vpc-egress` flag configures the necessary VPC Access Connector so the agent can communicate with the internal MCP server.
    *   Once complete, the script will provide a public URL to access your agent.



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