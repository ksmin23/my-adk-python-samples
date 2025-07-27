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

First, set up your project and enable the necessary APIs.

```bash
# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable the required APIs
gcloud services enable \
  alloydb.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  aiplatform.googleapis.com
```

### 2. Create an AlloyDB Cluster

Create an AlloyDB cluster and a primary instance. For simplicity, this guide uses public IP, but for production environments, it is recommended to use a private IP and a VPC network.

```bash
# Set environment variables
export ALLOYDB_REGION=your-alloydb-region
export ALLOYDB_CLUSTER=your-alloydb-cluster
export ALLOYDB_INSTANCE=your-alloydb-instance
export ALLOYDB_PASSWORD=your-db-password

# Create the AlloyDB cluster
gcloud alloydb clusters create $ALLOYDB_CLUSTER \
  --region=$ALLOYDB_REGION \
  --password=$ALLOYDB_PASSWORD \
  --project=YOUR_PROJECT_ID

# Create the primary instance
gcloud alloydb instances create $ALLOYDB_INSTANCE \
  --cluster=$ALLOYDB_CLUSTER \
  --region=$ALLOYDB_REGION \
  --instance-type=PRIMARY \
  --cpu-count=2 \
  --database-flags=google_ml_integration.enable_google_ml_integration=on

# Note: It may take a few minutes for the cluster and instance to be ready.
```

### 3. Grant IAM Permissions

Grant the necessary IAM roles to the service account that will be used to run the application.

```bash
# Set your service account email
export SERVICE_ACCOUNT=your-service-account@your-project-id.iam.gserviceaccount.com

# Grant the required roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/alloydb.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"
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

### 3. Run the Agent

You can run the agent using either the command-line interface or a web-based interface.

#### Using the Command-Line Interface (CLI)

Run the agent in your terminal using the `adk run` command.

```bash
adk run rag_with_alloydb
```

**Example Output:**

The example below shows the difference in the agent's responses before and after implementing RAG.

**Without RAG:**

The agent responds based on its general knowledge, which may be incorrect or not specific to the project's context.

```text
$ adk run rag_with_alloydb
Running agent rag_agent, type exit to exit.
[user]: What is ADK?
[rag_agent]: The ADK (Application Development Kit) is a set of APIs and services that allows an app to extend its functionality to the Android environment. It enables developers to integrate the app's features with the user's vehicle, such as starting and stopping the engine, controlling the air conditioning, and accessing vehicle information like tire pressure and fuel level. The ADK provides a secure way for apps to interact with vehicle systems.
[user]: Tell me main features of ADK
[rag_agent]: The ADK (Application Development Kit) offers several key features for developers:

*   **Vehicle Interaction:** It allows apps to interact with various vehicle systems, such as starting/stopping the engine, controlling air conditioning, and accessing vehicle data like tire pressure and fuel level.
*   **Security:** The ADK provides a secure framework for applications to communicate with the vehicle's systems.
*   **API and Services:** It is a collection of APIs and services designed to extend app functionality to the Android environment within a vehicle.
*   **Contextual Information:** It enables apps to leverage the in-vehicle context, enhancing the user experience by integrating vehicle-specific data and controls.
```

**With RAG:**

The agent uses the `search_documents_in_alloydb` tool to retrieve relevant information from the `source_documents` and provides an accurate answer based on that context.

```text
$ adk run rag_with_alloydb
Running agent rag_agent, type exit to exit.
[user]: What is ADK?
[rag_agent]: ADK (Agent Development Kit) is a framework designed to facilitate the development of Agentic AI applications on Google Cloud. It offers features such as declarative agent behavior definition, easy integration with LLMs like Gemini, the ability to define and utilize external APIs or services as 'tools', and support for RAG patterns using external data sources like Vector Search. ADK can be used for applications such as customer support chatbots, internal knowledge retrieval systems, and automating complex workflows.
[user]: Tell me main features of ADK.
[rag_agent]: The main features of ADK include:

*   **Declarative Approach:** Agents' behavior can be defined using configuration files instead of code.
*   **LLM Integration:** It allows for easy linkage with the latest Large Language Models like Gemini.
*   **Tool Usage:** External APIs or services can be defined as 'tools' for the agent to utilize.
*   **RAG Support:** It simplifies the implementation of RAG (Retrieval-Augmented Generation) patterns by leveraging external data sources like Vector Search.
```

#### Using the Web Interface

You can also interact with the agent through a web interface using the `adk web` command.

```bash
adk web rag_with_alloydb
```

**Screenshot:**

![ADK Web Interface for RAG with AlloyDB](assets/rag-with-alloydb.png)

## Reference

### Official Google Cloud Docs
- [Perform a vector search | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/perform-vector-search)
- [Run a vector similarity search | AlloyDB for PostgreSQL | Google ...](https://cloud.google.com/alloydb/docs/ai/run-vector-similarity-search)
- [Generate text embeddings](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings?resource=google_ml)

### Google Codelabs
- [Getting started with Vector Embeddings with AlloyDB AI](https://codelabs.developers.google.com/alloydb-ai-embedding#0)
- [Build a Patent Search App with AlloyDB, Vector Search & Vertex AI!](https://codelabs.developers.com/patent-search-alloydb-gemini#0)
- [Building a Smart Shop Agent with Gemini and AlloyDB Omni | Codelabs | Google for Developers](https://codelabs.developers.google.com/smart-shop-agent-alloydb#0)

### LangChain Integration
- [Google AlloyDB for PostgreSQL | 🦜️ LangChain](https://python.langchain.com/docs/integrations/vectorstores/google_alloydb/)