# Agentic RAG Project with AlloyDB Vector Search

This project is a sample implementation of an Agentic RAG using the Agent Development Kit (ADK) and the Vector Search feature of AlloyDB for PostgreSQL.

## Project Structure

```
/rag-with-alloydb
├── rag_with_alloydb/          # ADK Agent directory
│   └── requirements.txt     # Agent dependencies
├── data_ingestion/          # Data ingestion directory
│   └── requirements.txt     # Data ingestion script dependencies
├── source_documents/        # Source documents for RAG
└── README.md
```

## Prerequisites

Before you begin, you need to have an active Google Cloud project and an AlloyDB cluster.

### 1. Configure your Google Cloud project

First, you need to authenticate with Google Cloud. Run the following command and follow the instructions to log in.

```bash
gcloud auth application-default login
```

Next, set up your project, enable the necessary APIs, and create a service account with the required permissions.

```bash
# Set your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Enable the required APIs
gcloud services enable \
  alloydb.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com

# Create a service account for local execution and data ingestion
export SERVICE_ACCOUNT="alloydb-rag-sa"
gcloud iam service-accounts create $SERVICE_ACCOUNT \
    --description="Service account for the AlloyDB RAG sample" \
    --display-name="AlloyDB RAG SA"

# Grant the required roles to the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/alloydb.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 2. Create an AlloyDB Cluster and primary instance

Create an AlloyDB cluster and a primary instance using the `gcloud` CLI. For simplicity, this guide uses public IP, but for production environments, it is recommended to use a private IP and a VPC network.

Alternatively, you can create the cluster and instance using the Google Cloud Console. Follow the instructions in the [official documentation](https://cloud.google.com/alloydb/docs/ai/perform-vector-search).

```bash
# Set environment variables
export ALLOYDB_REGION="your-alloydb-region"
export ALLOYDB_CLUSTER="your-alloydb-cluster"
export ALLOYDB_INSTANCE="your-alloydb-instance"
export ALLOYDB_PASSWORD="your-db-password"
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export VPC_NETWORK="your-vpc-network"

# Create the AlloyDB cluster
gcloud alloydb clusters create $ALLOYDB_CLUSTER \
  --region=$ALLOYDB_REGION \
  --password=$ALLOYDB_PASSWORD \
  --network="projects/${PROJECT_NUMBER}/global/networks/${VPC_NETWORK}" \
  --project=$PROJECT_ID

# Create the primary instance
gcloud alloydb instances create $ALLOYDB_INSTANCE \
  --cluster=$ALLOYDB_CLUSTER \
  --region=$ALLOYDB_REGION \
  --instance-type=PRIMARY \
  --cpu-count=8 \
  --database-flags=google_ml_integration.enable_model_support=on,password.enforce_complexity=on \
  --assign-inbound-public-ip=ASSIGN_IPV4

# Note: It may take a few minutes for the cluster and instance to be ready.
```

### 3. Configure the Database

After creating the cluster and instance, connect to your database using AlloyDB Studio in the Google Cloud console to enable the necessary extensions and grant permissions.

1.  Navigate to the **AlloyDB clusters** page in the Google Cloud console.
2.  Find your cluster and click **Connect** under the **Actions** column.
3.  Select **AlloyDB Studio** and sign in with your database user and password.
4.  In the query editor, run the following SQL commands to enable the required extensions:

    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS google_ml_integration;
    ```

5.  Grant the `EXECUTE` permission on the `embedding` function to your database user. This allows the user to generate embeddings.

    ```sql
    GRANT EXECUTE ON FUNCTION embedding TO postgres;
    ```

> **Note**: This example uses `postgres` as the username because it is the default user created when setting up the database.

### 4. Grant Vertex AI permissions to AlloyDB

To allow AlloyDB to call the Vertex AI embedding models, you must grant the "Vertex AI User" role to the AlloyDB service account.

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
    --role="roles/alloydb.serviceAgent"
```

### 5. Grant Agent Engine permissions to AlloyDB

To allow the deployed Agent Engine to connect to your AlloyDB instance, you must grant the `AlloyDB Client` role to the Agent Engine's service account.

```bash
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/alloydb.client"
```

## Setup

### 1. Install Dependencies

This project uses `uv` to manage the Python virtual environment and package dependencies.

**Create and activate the virtual environment:**
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
# Install agent dependencies
uv pip install -r rag_with_alloydb/requirements.txt

# Install data ingestion script dependencies
uv pip install -r data_ingestion/requirements.txt
```

### 2. Data Ingestion

Run the `data_ingestion/ingest.py` script to load the documents from `source_documents` into AlloyDB.

First, you need to create a `.env` file for the data ingestion script by copying the example file and filling in the required values.

```bash
cp data_ingestion/.env.example data_ingestion/.env
# Now, open data_ingestion/.env in an editor and modify the values.
```

Once the `.env` file is ready, you can run the data ingestion script with the following command. You can also override the values in the `.env` file using command-line arguments.

**Example:**
```bash
python data_ingestion/ingest.py \
  --database="your-alloydb-database" \
  --table_name="vector_store" \
  --user="your-db-user" \
  --password="your-db-password" \
  --source_dir="source_documents/"
```

### 3. Run the Agent Locally

Before running the agent, you need to create a `.env` file in the `rag_with_alloydb` directory. Copy the example file and fill in the required values for your environment.

```bash
cp rag_with_alloydb/.env.example rag_with_alloydb/.env
# Now, open rag_with_alloydb/.env in an editor and modify the values.
```

You can run the agent using either the command-line interface or a web-based interface.

#### Using the Command-Line Interface (CLI)

Run the agent in your terminal using the `adk run` command.

```bash
adk run rag_with_alloydb
```

#### Using the Web Interface

You can also interact with the agent through a web interface using the `adk web` command.

```bash
adk web
```

**Screenshot:**

![ADK Web Interface for RAG with AlloyDB](assets/rag-with-alloydb.png)

## Deployment

The RAG with AlloyDB agent can be deployed to Vertex AI Agent Engine using the following commands.

### 1. Set Environment Variables

Before running the deployment script, you need to set the following environment variables.

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="your-gcp-location"
export GOOGLE_CLOUD_STORAGE_BUCKET="your-gcs-bucket-for-staging"
```

### 2. Install Deployment Dependencies

You will need to install `google-cloud-aiplatform` with the `agent_engines` extra.
```bash
uv pip install "google-cloud-aiplatform[agent_engines]>=1.91.0,!=1.92.0" cloudpickle absl-py
```

### 3. Run the Deployment Script

```bash
python3 deployment/deploy.py --create
```

When the deployment finishes, it will print a line like this:
```
Created remote agent: projects/<PROJECT_NUMBER>/locations/<PROJECT_LOCATION>/reasoningEngines/<AGENT_ENGINE_ID>
```
Make a note of the `AGENT_ENGINE_ID`. You will need it to interact with your deployed agent.

If you forgot the ID, you can list existing agents using:
```bash
python3 deployment/deploy.py --list
```

To delete the deployed agent, you may run the following command:
```bash
python3 deployment/deploy.py --delete --resource_id=${AGENT_ENGINE_ID}
```

### 4. Interact with the Deployed Agent

You can interact with your deployed agent using a simple Python script.

**a. Set Environment Variables:**
Ensure the following environment variables are set in your terminal. You will need the `AGENT_ENGINE_ID` from the deployment step.

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="your-gcp-location"
export AGENT_ENGINE_ID="your-agent-engine-id"
```

**b. Create and Run the Python Script:**
Create a file named `query_agent.py` and add the following code.

```python
import os
import vertexai
from vertexai import agent_engines

def query_remote_agent(project_id, location, agent_id, user_query):
    """Initializes Vertex AI and sends a query to the deployed agent."""
    vertexai.init(project=project_id, location=location)

    # Load the deployed agent
    remote_agent = agent_engines.get(agent_id)
    remote_session = remote_agent.create_session(user_id="u_123")

    print(f"Querying agent: '{user_query}'...")

    # Stream the query and print the final text response
    for event in remote_agent.stream_query(
        user_id="u_123",
        session_id=remote_session["id"],
        message=user_query
    ):
        if event.get('content', {}).get('parts', [{}])[0].get('text'):
            print("Response:", event['content']['parts'][0]['text'])

if __name__ == "__main__":
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    loc = os.getenv("GOOGLE_CLOUD_LOCATION")
    agent = os.getenv("AGENT_ENGINE_ID")
    
    if not all([project, loc, agent]):
        print("Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, and AGENT_ENGINE_ID environment variables must be set.")
    else:
        query = "What is ADK?"
        query_remote_agent(project, loc, agent, query)
```

**c. Run the script:**
```bash
python query_agent.py
```

**Example Output:**
```
Querying agent: 'What is ADK?'...
Response: ADK (Agent Development Kit) is a framework designed to help develop Agentic AI applications on Google Cloud. It allows for defining an agent's behavior through configuration files rather than code, integrates with Large Language Models (LLMs) like Gemini, enables the use of external APIs or services as tools, and supports RAG (Retrieval Augmented Generation) patterns leveraging external data sources.

ADK Agents are core components for building autonomous applications within this framework, with a `BaseAgent` class providing the fundamental structure. There are different types of agents, including LLM Agents that use LLMs for understanding and decision-making, and Workflow Agents that control the execution flow of other agents.

ADK also integrates with MCP (Model Context Protocol), an open standard that standardizes LLM communication with external systems, simplifying how LLMs get context, perform actions, and interact with data sources and tools.
```

## Reference

#### Official Google Cloud Docs
- [Perform a vector search | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/perform-vector-search)
- [Run a vector similarity search | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/run-vector-similarity-search)
- [Run a hybrid vector similarity search | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/run-hybrid-vector-similarity-search)
- [Choose an indexing strategy | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/choose-index-strategy)
- [Generate text embeddings](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings?resource=google_ml)
- [Announcing ScaNN: Efficient Vector Similarity Search](https://research.google/blog/announcing-scann-efficient-vector-similarity-search/)

#### Google Codelabs
- [Getting started with Vector Embeddings with AlloyDB AI](https://codelabs.developers.google.com/alloydb-ai-embedding#0)
- [Build a Patent Search App with AlloyDB, Vector Search & Vertex AI!](https://codelabs.developers.com/patent-search-alloydb-gemini#0)
- [Building a Smart Shop Agent with Gemini and AlloyDB Omni | Codelabs | Google for Developers](https://codelabs.developers.google.com/smart-shop-agent-alloydb#0)

#### LangChain Integration
- [Google AlloyDB for PostgreSQL | 🦜️ LangChain](https://python.langchain.com/docs/integrations/vectorstores/google_alloydb/)
