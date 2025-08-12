# Agentic RAG with Vertex AI RAG Engine

This project is a sample implementation of an Agentic RAG (Retrieval-Augmented Generation) application using the Google Agent Development Kit (ADK). It leverages the managed **Vertex AI RAG Engine**, which uses a **Vertex AI Vector Search** index as its backend for efficient, scalable document retrieval.

## Project Structure

```
/rag-engine-with-vectorsearch
├── deployment/                  # Scripts for deploying the agent
│   ├── deploy.py
│   └── ...
├── rag_engine_with_vectorsearch/   # ADK Agent directory
│   ├── .env.example
│   ├── agent.py                 # Core agent logic
│   ├── prompt.py                # Agent's instructional prompt
│   └── requirements.txt         # Agent dependencies
├── data_ingestion/              # Data ingestion scripts
│   ├── .env.example
│   ├── create_vector_search_index.py # Creates the backend Vector Search index
│   ├── ingest.py                # Creates the RAG Corpus and ingests data
│   └── requirements.txt         # Data ingestion script dependencies
└── README.md
```

## Architecture

This project uses the managed Vertex AI RAG Engine to simplify the retrieval process. The architecture works as follows:

1.  **User Query**: A user sends a query to the ADK agent, which is deployed on Vertex AI Agent Engine.
2.  **Context Retrieval**: The agent's `VertexAiRagRetrieval` tool automatically queries the Vertex AI RAG Engine with the user's question.
3.  **Return Context**: The RAG Engine, backed by a powerful Vertex AI Vector Search index, finds the most relevant document chunks and returns them as context.
4.  **Generate Response**: The agent uses the retrieved context to generate a comprehensive and accurate answer for the user.

### Architecture Diagram

```text
+--------------+   (1) Query    +----------------------------+   (2) Retrieve Context  +-------------------------+
|              | -------------> |      ADK Agent             | ----------------------> |   Vertex AI RAG Engine  |
|  User/Client |              | (on Vertex AI Agent Engine)  |                         |   (RAG Corpus)          |
|              | <------------- |                            | <---------------------- |                         |
+--------------+  (4) Response  +----------------------------+   (3) Return Context    +-------------------------+
                                                                                                    |
                                                                                                    |
                                                                                                    |
                                                                                                    |
                                                                                                    |
                                                                                                    | (Uses)
                                                                                                    v
                                                                                    +---------------------------+
                                                                                    | Vertex AI Vector Search   |
                                                                                    |    (Backing Index)        |
                                                                                    +---------------------------+
```

## Prerequisites

Before you begin, you need to have an active Google Cloud project and the `gcloud` CLI installed.

### 1. Configure your Google Cloud project

First, authenticate with Google Cloud. Run the following command and follow the instructions to log in.

```bash
gcloud auth application-default login
```

Next, set up your project and enable the necessary APIs.

```bash
# Set your project ID and location
export PROJECT_ID=$(gcloud config get-value project)
export LOCATION="us-central1" # Or your preferred location

# Enable the required APIs
gcloud services enable \
  aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 2. Grant Agent Engine Permissions

To allow the deployed Agent Engine to access your RAG Corpus and Vector Search index, you must grant the `Vertex AI User` role to the Agent Engine's service account.

```bash
# Get your project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant the Vertex AI User role to the Agent Engine service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

Without this permission, you will encounter a `403 IAM_PERMISSION_DENIED` error when the deployed agent tries to query the RAG Engine.

## Setup and Data Ingestion

The setup process involves creating the necessary backend infrastructure (Vector Search), preparing your source documents, and ingesting them into the RAG Engine.

### 1. Install Dependencies

This project uses `uv` to manage the Python virtual environment and package dependencies.

**Create and activate the virtual environment:**
From the root of the `rag-engine-with-vectorsearch` directory:
```bash
# Create the virtual environment
uv venv

# Activate the virtual environment (macOS/Linux)
source .venv/bin/activate
# Activate the virtual environment (Windows)
.venv\Scripts\activate
```

**Install dependencies:**
```bash
# Install agent and deployment dependencies
uv pip install -r rag_engine_with_vectorsearch/requirements.txt
uv pip install "google-cloud-aiplatform[agent_engines,rag]>=1.108.0" absl-py

# Install data ingestion script dependencies
uv pip install -r data_ingestion/requirements.txt
```

### 2. Create Backend Infrastructure (Vector Search)

The RAG Engine requires a Vertex AI Vector Search index to operate. The provided script automates its creation.

**Run the index creation script:**
The `create_vector_search_index.py` script creates both the index and a public endpoint. You must provide a name for your index. The script defaults to an embedding dimension of 768, suitable for models like `text-embedding-005`. If you use a different model, specify the correct dimension using the `--embedding_dim` flag.

*Note: This process can take 20-30 minutes to complete.*

```bash
# Navigate to the data ingestion directory
cd data_ingestion

# Run the script with a specified index name
python create_vector_search_index.py --index_name="my-rag-index"
```

The script will output the **Index ID** and **Endpoint ID**. **Save these values**, as you will need them for the next step.

### 3. Ingest Your Data into RAG Engine

Now, you will create a RAG Corpus and ingest documents into it.

**Run the data ingestion script:**
The `ingest.py` script creates the RAG Corpus, links it to your Vector Search index, and imports documents. This example uses a sample of Alphabet earnings reports that's uploaded to a public GCS bucket.

```bash
# From the data_ingestion directory
python ingest.py \
  --project_id="$PROJECT_ID" \
  --location="$LOCATION" \
  --index_id="your-vector-search-index-id" \
  --endpoint_id="your-vector-search-endpoint-id" \
  --corpus_display_name="my-adk-rag-corpus" \
  --gcs_source_uri="gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs"
```
This script will output the **RAG Corpus resource name**. Save this value for the next step.

**Grant RAG Engine GCS Access (For Your Own Data):**
If you want to use your own documents from a private GCS bucket, you must grant the `Storage Object Viewer` role to the Vertex RAG service account to allow it to read your files.
```bash
# Grant the required role to the RAG Engine service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-vertex-rag.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

### 4. Run the Agent Locally

Before running the agent, create a `.env` file in the `rag_engine_with_vectorsearch` directory. Copy the example file and fill in the `RAG_CORPUS` resource name from the previous step.

```bash
# Navigate back to the project root
cd ..

# Create the .env file
cp rag_engine_with_vectorsearch/.env.example rag_engine_with_vectorsearch/.env

# Now, open rag_engine_with_vectorsearch/.env in an editor and set the RAG_CORPUS value.
# e.g., RAG_CORPUS="projects/your-project-number/locations/us-central1/ragCorpora/your-corpus-id"
```

You can now run the agent locally using the ADK CLI.

#### Using the Command-Line Interface (CLI)
```bash
adk run rag_engine_with_vectorsearch
```

#### Using the Web Interface
```bash
adk web
```

**Screenshot:**

![ADK Web Interface for RAG with RAG Engine](assets/rag-engine-with-vectorsearch.png)

## Deployment

The agent can be deployed to a scalable, serverless environment on **Vertex AI Agent Engine**.

### 1. Set Environment Variables

The deployment script uses these environment variables.
```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="your-gcp-location" # e.g., us-central1
export GOOGLE_CLOUD_STORAGE_BUCKET="your-gcs-bucket-for-staging" # A bucket for deployment artifacts
```
*Note: If the staging bucket doesn't exist, it will be created automatically.*

### 2. Run the Deployment Script

Navigate to the `deployment` directory and run the script with the `create` action.

```bash
python deployment/deploy.py create
```

When the deployment finishes, it will print a line like this:
`Successfully created remote agent: projects/<PROJECT_NUMBER>/locations/<LOCATION>/agentEngines/<AGENT_ENGINE_ID>`

Make a note of the `AGENT_ENGINE_ID`.

### 3. Interact with the Deployed Agent

You can interact with your deployed agent using the provided Python script.

**a. Set Environment Variables:**
Ensure the following environment variables are set. Use the `AGENT_ENGINE_ID` from the deployment step.

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="your-gcp-location"
export AGENT_ENGINE_ID="your-agent-engine-id"
```

**b. Create and Run the Python Script:**
Create a file named `query_agent.py` in the project root and add the following code.

```python
import os
import vertexai
from vertexai import agent_engines

def query_remote_agent(project_id, location, agent_id, user_query):
    """Initializes Vertex AI and sends a query to the deployed agent."""
    vertexai.init(project=project_id, location=location)

    # Load the deployed agent
    remote_agent = agent_engines.get(agent_id)
    
    print(f"Querying agent: '{user_query}'...")

    # Stream the query and print the final text response
    response = remote_agent.query(
        message=user_query
    )
    print("Response:", response['output'])

if __name__ == "__main__":
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    loc = os.getenv("GOOGLE_CLOUD_LOCATION")
    agent = os.getenv("AGENT_ENGINE_ID")
    
    if not all([project, loc, agent]):
        print("Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and AGENT_ENGINE_ID environment variables must be set.")
    else:
        query = "What are the key business segments mentioned in Alphabet's 2024 Q4 earning releases?"
        query_remote_agent(project, loc, agent, query)
```

**c. Run the script:**
```bash
python query_agent.py
```

## Clean up

To avoid incurring future charges, delete the cloud resources you created.

```bash
# Delete the Agent Engine
python deployment/deploy.py delete --resource-id=${AGENT_ENGINE_ID}

# Delete the RAG Corpus
# Note: As of August 2025, there is no gcloud command to delete a RAG corpus.
# Please delete it from the Google Cloud Console (Vertex AI > RAG Management).

# Delete the Vector Search Endpoint (Find the ID from the gcloud console)
gcloud ai index-endpoints delete YOUR_ENDPOINT_ID --region=$LOCATION

# Delete the Vector Search Index (Find the ID from the gcloud console)
gcloud ai indexes delete YOUR_INDEX_ID --region=$LOCATION

# Delete the GCS bucket for staging
gsutil rm -r gs://$GOOGLE_CLOUD_STORAGE_BUCKET
```

## References

- [Vertex AI RAG Engine Documentation](https://cloud.google.com/vertex-ai/docs/rag)
- [Agent Development Kit (ADK) Documentation](https://cloud.google.com/adk/docs)
- [Vertex AI Vector Search Documentation](https://cloud.google.com/vertex-ai/docs/vector-search)