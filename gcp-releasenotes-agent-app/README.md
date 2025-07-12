# Google Cloud Release Notes Agent

This agent is designed to answer questions about Google Cloud Release notes. It utilizes the Google ADK (Agent Development Kit) and connects to a Toolbox service to query information.

## Prerequisites

Before running the agent, ensure you have the following installed and configured:

1.  **Python 3.x**
2.  **Google Cloud SDK (`gcloud`)**: If you don't have it, [install it from here](https://cloud.google.com/sdk/docs/install).
3.  **Authentication**: You must authenticate with Google Cloud to allow the agent to access the necessary services. Run the following command in your terminal:
    ```bash
    gcloud auth application-default login
    ```

## Installation

1.  Clone the repository to your local machine.
2.  Navigate to the `gcp-releasenotes-agent-app` directory.
3.  Install the required Python packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

-   **Toolbox Endpoint**: The agent connects to a Toolbox service defined by the `TOOLBOX_ENDPOINT` variable in `agent.py`. The default is set to `https://toolbox-vsi6xb4zha-uc.a.run.app`.
-   **Authentication**: Authentication is handled automatically by obtaining a Google ID token from the credentials configured via the `gcloud` command in the prerequisites.
-   **Tools**: The agent loads a toolset named `my_bq_toolset` from the Toolbox service.

## How to Run

This agent is designed to be run with the Google ADK CLI.

To start the agent and interact with it through a web interface, run the following command from the parent directory (`my-agents/`):

```bash
adk web -m gcp-releasenotes-agent-app
```

This will start a local web server where you can test and interact with the agent.

## Dependencies

This project relies on the following major packages:

-   `google-adk==1.5.0`
-   `toolbox-core==0.3.0`

## References

- [Build a Travel Agent using MCP Toolbox for Databases and Agent ...](https://codelabs.developers.google.com/travel-agent-mcp-toolbox-adk#0)
- [Build a Sports Shop Agent AI Assistant with ADK, MCP Toolbox and AlloyDB](https://codelabs.developers.google.com/codelabs/devsite/codelabs/sports-agent-adk-mcp-alloydb#0)
- [MCP Toolbox for Databases](https://googleapis.github.io/genai-toolbox/getting-started/)
- [toolbox-core · PyPI](https://pypi.org/project/toolbox-core/)
- [googleapis/mcp-toolbox-sdk-python: Python SDK for ... - GitHub](https://github.com/googleapis/mcp-toolbox-sdk-python)