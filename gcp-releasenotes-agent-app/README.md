# Google Cloud Release Notes Agent

This agent is designed to answer questions about Google Cloud Release Notes. It utilizes the Google Agent Development Kit (ADK) and connects to the [MCP Toolbox for Databases](https://googleapis.github.io/genai-toolbox/getting-started/) to query information.

The core logic is in `gcp_releasenotes_agent/agent.py`.

## Prerequisites

Before running the agent, ensure you have the following:

1.  **Python & ADK**: Python 3.x and the Google Agent Development Kit are installed.
2.  **Google Cloud SDK (`gcloud`)**: If you don't have it, [install it from here](https://cloud.google.com/sdk/docs/install).
3.  **Authentication**: You must authenticate with Google Cloud for the agent to access the necessary services. Run the following command in your terminal:
    ```bash
    gcloud auth application-default login
    ```

## Setup and Local Execution

1.  **Navigate to the Agent Directory**:
    From the root of the `my-agents` repository, change to this agent's directory:
    ```bash
    cd gcp-releasenotes-agent-app
    ```

2.  **Install Dependencies**:
    Install the required Python packages:
    ```bash
    uv pip install -r gcp_releasenotes_agent/requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file for the agent by copying the example:
    ```bash
    cp gcp_releasenotes_agent/.env.example gcp_releasenotes_agent/.env
    ```
    *Note: The default `.env` file is often sufficient for local execution, but you can edit it if you need to customize the `TOOLBOX_ENDPOINT`.*

4.  **Run the Agent Locally**:
    To start the agent and interact with it through the ADK's web interface, run the following command from the `gcp-releasenotes-agent-app/` directory:
    ```bash
    adk web
    ```
    This will start a local web server where you can test the agent.

## Deploying to Cloud Run

You can deploy this agent as a containerized application on Google Cloud Run using the ADK CLI. The ADK automatically handles containerization, so a manual `Dockerfile` is not needed.

1.  **Authenticate with Google Cloud**:
    If you haven't already, authenticate your user account:
    ```bash
    gcloud auth login
    ```

2.  **Set Project and Location**:
    Set your default project and region to simplify the deployment command.
    ```bash
    # Replace with your actual project ID and desired region
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    ```

3.  **Deploy**:
    From the `gcp-releasenotes-agent-app/` directory, run the following command to deploy the agent:
    ```bash
    adk deploy cloud_run \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name="gcp-releasenotes-agent-service" \
        --with_ui \
        ./gcp_releasenotes_agent
    ```
    During deployment, you may be prompted to allow unauthenticated invocations. Once complete, the ADK will provide a URL to access your agent on Cloud Run.

## Configuration Details

-   **Toolbox Endpoint**: The agent connects to a Toolbox service defined by the `TOOLBOX_ENDPOINT` variable in `gcp_releasenotes_agent/agent.py`.
-   **Authentication**: The agent automatically obtains a Google ID token from the credentials configured via the `gcloud auth` command.
-   **Tools**: The agent is configured to load a toolset named `my_bq_toolset` from the Toolbox service.

## Dependencies

This project relies on the following major packages:

-   `google-adk==1.5.0`
-   `toolbox-core==0.3.0`

## References

- [Build a Travel Agent using MCP Toolbox for Databases and Agent Development Kit (ADK)](https://codelabs.developers.google.com/travel-agent-mcp-toolbox-adk#0)
- [Build a Sports Shop Agent AI Assistant with ADK, MCP Toolbox and AlloyDB](https://codelabs.developers.google.com/codelabs/devsite/codelabs/sports-agent-adk-mcp-alloydb#0)
- [MCP Toolbox for Databases](https://googleapis.github.io/genai-toolbox/getting-started/)
- [toolbox-core - PyPI](https://pypi.org/project/toolbox-core/)
- [googleapis/mcp-toolbox-sdk-python: Python SDK for interacting with the MCP Toolbox for Databases. - GitHub](https://github.com/googleapis/mcp-toolbox-sdk-python)
