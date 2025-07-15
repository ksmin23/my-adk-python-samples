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

## Deploying to Cloud Run

You can deploy this agent as a containerized application on Google Cloud Run. There are two ways to do this:

### ADK CLI 사용 (권장)

`adk` 커맨드라인 도구를 사용하는 것이 가장 간단한 배포 방법입니다.

1.  **Google Cloud 인증**:
    먼저 다음 명령어를 실행하여 Google Cloud�� 인증합니다.
    ```bash
    gcloud auth login
    ```

2.  **프로젝트 및 위치 설정**:
    배포를 간소화하기 위해 다음 환경 변수를 설정할 수 있습니다.
    ```bash
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    export AGENT_PATH="./gcp-releasenotes-agent-app"
    export SERVICE_NAME="gcp-releasenotes-agent-service"
    export APP_NAME="gcp-releasenotes-agent-app"
    ```
    또는 `gcloud` 명령어로 직접 프로젝트와 리전을 설정할 수도 있습니다.
    ```bash
    gcloud config set project [PROJECT_ID]
    gcloud config set compute/region [REGION]
    ```
    `[PROJECT_ID]`와 `[REGION]`을 실제 값으로 바꾸세요 (예: `us-central1`).

3.  **배포**:
    프로젝트의 루트 디렉토리 (`my-agents/`)에서 다음 명령어를 실행하여 에이전트를 배포합니다.
    ```bash
    adk deploy cloud_run \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service_name=$SERVICE_NAME \
        --app_name=$APP_NAME \
        --with_ui \
        $AGENT_PATH
    ```
    배포 과정에서 서비스에 대한 인증되지 않은 호출을 허용할지 묻는 메시지가 표시될 수 있습니다.

    ADK는 컨테이너화 및 배포 프로세스를 자동으로 처리합니다. 배포가 완료되면 Cloud Run에서 에이전트에 액세스할 수 있는 URL을 제공합니다.

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
COPY gcp-releasenotes-agent-app/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY gcp-releasenotes-agent-app/ /app/gcp-releasenotes-agent-app/

# Expose the port that the ADK web server will run on
EXPOSE 8080

# Set the command to run the application
# The ADK web server will bind to 0.0.0.0:8080 by default
CMD ["adk", "web", "-m", "gcp-releasenotes-agent-app"]
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
    gcloud builds submit --tag gcr.io/[PROJECT_ID]/gcp-releasenotes-agent
    ```

3.  **Deploy the image to Cloud Run**:
    Replace `[PROJECT_ID]` and `[REGION]` with your project ID and desired region (e.g., `us-central1`).
    ```bash
    gcloud run deploy gcp-releasenotes-agent --image gcr.io/[PROJECT_ID]/gcp-releasenotes-agent --platform managed --region [REGION] --allow-unauthenticated
    ```
    This command deploys the agent and makes it publicly accessible. For production environments, you should configure appropriate authentication.

After deployment, Cloud Run will provide a URL where your agent is accessible.

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