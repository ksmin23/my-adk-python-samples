# Agentic RAG Project with Spanner Vector Search

This project is a sample implementation of an Agentic RAG using the Agent Development Kit (ADK) and the Vector Search feature of Google Cloud Spanner.

## Project Structure

```
/rag-with-spanner
├── rag_with_spanner/        # ADK Agent directory
│   └── requirements.txt     # Agent dependencies
├── data_ingestion/          # Data ingestion directory
│   └── requirements.txt     # Data ingestion script dependencies
├── source_documents/        # Source documents for RAG
└── README.md
```

## Prerequisites

Before you begin, you need to have an active Google Cloud project and a Spanner instance.

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
  spanner.googleapis.com \
  aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com

# Create a service account for local execution and data ingestion
export SERVICE_ACCOUNT="spanner-rag-sa"
gcloud iam service-accounts create $SERVICE_ACCOUNT \
    --description="Service account for the Spanner RAG sample" \
    --display-name="Spanner RAG SA"

# Grant the required roles to the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/spanner.databaseUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 2. Create a Spanner Instance and Database

Create a Spanner instance and a database using the `gcloud` CLI.

```bash
# Set environment variables
export SPANNER_INSTANCE="your-spanner-instance"
export SPANNER_DATABASE="your-spanner-database"
export SPANNER_REGION="your-spanner-region"

# Create the Spanner instance
gcloud spanner instances create $SPANNER_INSTANCE \
  --config=regional-$SPANNER_REGION \
  --description="Spanner instance for RAG" \
  --nodes=1

# Create the database
gcloud spanner databases create $SPANNER_DATABASE \
  --instance=$SPANNER_INSTANCE
```

### 3. Configure the Database Table

After creating the instance and database, you need to create a table to store the vectors. You can do this using the `gcloud` CLI.

The table should have columns for `content`, `embedding`, and a primary key. The `embedding` column must be of type `ARRAY<FLOAT64>`.

```bash
# Create the vector store table
gcloud spanner databases ddl update $SPANNER_DATABASE --instance=$SPANNER_INSTANCE \
  --ddl='CREATE TABLE vector_store (
            id STRING(36) NOT NULL,
            content STRING(MAX),
            embedding ARRAY<FLOAT64>(768)
         ) PRIMARY KEY (id)'
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
uv pip install -r rag_with_spanner/requirements.txt

# Install data ingestion script dependencies
uv pip install -r data_ingestion/requirements.txt
```

### 2. Data Ingestion

Run the `data_ingestion/ingest.py` script to load the documents from `source_documents` into Spanner.

First, you need to create a `.env` file for the data ingestion script by copying the example file and filling in the required values.

```bash
cp data_ingestion/.env.example data_ingestion/.env
# Now, open data_ingestion/.env in an editor and modify the values.
```

Once the `.env` file is ready, you can run the data ingestion script with the following command.

**Example:**
```bash
python data_ingestion/ingest.py \
  --instance_id="your-spanner-instance" \
  --database_id="your-spanner-database" \
  --table_name="vector_store" \
  --source_dir="source_documents/"
```

### 3. Run the Agent Locally

Before running the agent, you need to create a `.env` file in the `rag_with_spanner` directory. Copy the example file and fill in the required values for your environment.

```bash
cp rag_with_spanner/.env.example rag_with_spanner/.env
# Now, open rag_with_spanner/.env in an editor and modify the values.
```

You can run the agent using either the command-line interface or a web-based interface.

#### Using the Command-Line Interface (CLI)

Run the agent in your terminal using the `adk run` command.

```bash
adk run rag_with_spanner
```

#### Using the Web Interface

You can also interact with the agent through a web interface using the `adk web` command.

```bash
adk web rag_with_spanner
```

## Deployment

The RAG with Spanner agent can be deployed to Vertex AI Agent Engine using the `deployment/deploy.py` script. The usage is the same as the `rag-with-alloydb` example. Refer to its `README.md` for detailed deployment and interaction instructions.
