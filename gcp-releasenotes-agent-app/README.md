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
    uv pip install -r gcp_releasenotes_agent/requirements.txt
    ```

## Configuration

-   **Toolbox Endpoint**: The agent connects to a Toolbox service defined by the `TOOLBOX_ENDPOINT` variable in `gcp_releasenotes_agent/agent.py`.
-   **Authentication**: Authentication is handled automatically by obtaining a Google ID token from the credentials configured via the `gcloud` command in the prerequisites.
-   **Tools**: The agent loads a toolset named `my_bq_toolset` from the Toolbox service.

## How to Run

This agent is designed to be run with the Google ADK CLI.

To start the agent and interact with it through a web interface, run the following command from the parent directory (`gcp-releasenotes-agent-app/`):

```bash
adk web
```

This will start a local web server where you can test and interact with the agent.

## Deploying to Cloud Run

You can deploy this agent as a containerized application on Google Cloud Run. There are two ways to do this:

### Using the ADK CLI (Recommended)

Using the `adk` command-line tool is the simplest way to deploy the agent.

1.  **Authenticate with Google Cloud**:
    First, run the following command to authenticate with Google Cloud:
    ```bash
    gcloud auth login
    ```

2.  **Set Project and Location**:
    To simplify the deployment process, you can set the following environment variables:
    ```bash
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    export AGENT_PATH="./gcp_releasenotes_agent"
    export SERVICE_NAME="gcp-releasenotes-agent-service"
    export APP_NAME="gcp-releasenotes-agent-app"
    ```
    Alternatively, you can set the project and region directly using `gcloud` commands:
    ```bash
    gcloud config set project [PROJECT_ID]
    gcloud config set compute/region [REGION]
    ```
    Replace `[PROJECT_ID]` and `[REGION]` with your actual values (e.g., `us-central1`).

3.  **Deploy**:
    From the project's root directory (`gcp-releasenotes-agent-app/`), run the following command to deploy the agent:
    ```bash
    adk deploy cloud_run \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name=$SERVICE_NAME \
        --app_name=$APP_NAME \
        --with_ui \
        $AGENT_PATH
    ```
    During the deployment, you may be prompted to allow unauthenticated invocations for the service.

    The ADK automatically handles the containerization and deployment process. Once complete, it will provide a URL to access your agent on Cloud Run.


### Using a Dockerfile (Manual Method)

For more control over the build process, you can use a `Dockerfile`.

#### 1. Create a `Dockerfile`

Create a file named `Dockerfile` in the root of your project (`my-agents/`) with the following content:

```Dockerfile
# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to be sent straight to the terminal
ENV PYTHONUNBUFFERED TRUE

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY gcp_releasenotes_agent/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY gcp_releasenotes_agent/ /app/gcp_releasenotes_agent/

# Expose the port that the ADK web server will run on
EXPOSE 8080

# Set the command to run the application
# The ADK web server will bind to 0.0.0.0:8080 by default
CMD ["adk", "web", "-m", "gcp_releasenotes_agent"]
```

#### 2. Build and Deploy

1.  **Enable Services**:
    If you haven't already, enable the Cloud Build and Cloud Run APIs:
    ```bash
    gcloud services enable cloudbuild.googleapis.com run.googleapis.com
    ```

2.  **Build the container image using Cloud Build**:
    Replace `[PROJECT_ID]` with your Google Cloud project ID.
    ```bash
    gcloud builds submit --tag [REGION]-docker.pkg.dev/[PROJECT_ID]/[REPOSITORY_NAME]/gcp-releasenotes-agent:latest .
    ```

3.  **Deploy the image to Cloud Run**:
    Replace `[PROJECT_ID]` and `[REGION]` with your project ID and desired region (e.g., `us-central1`).
    ```bash
    gcloud run deploy gcp-releasenotes-agent \
        --image gcr.io/[PROJECT_ID]/gcp-releasenotes-agent \
        --region [REGION] \
        --allow-unauthenticated \
        # --network [VPC] \
        # --subnet [SUBNET] \
    ```
    This command deploys the agent and makes it publicly accessible. For production environments, you should configure appropriate authentication.

After deployment, Cloud Run will provide a URL where your agent is accessible.

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