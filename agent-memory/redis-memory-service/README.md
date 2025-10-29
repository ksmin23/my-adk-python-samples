# ADK Redis Memory Service Example

This project contains a sample agent built with [ADK Python](https://google.github.io/adk-docs/) that demonstrates how to implement a custom long-term memory service using Redis.

ADK's memory services provide an interface for creating and searching for memories across user sessions. This project implements a custom `MemoryService` that adheres to ADK's `BaseMemoryService` interface, using Redis's Vector Search feature as the backend for this searchable, long-term knowledge store.

This approach leverages the concepts of the [Vertex AI Agent Engine Memory Bank](https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/overview), allowing the agent to dynamically generate and access personalized long-term memories. This enhances personalization and creates continuity across multiple conversations with a user.

---

## Directory Structure

The project is organized as follows:

```
./redis-memory-service
├── adk_cli.py
├── README.md
├── notebooks
│   └── get_started_with_adk_redis_memory_service.ipynb
└── redis_memory_service
    ├── __init__.py
    ├── .ae_ignore
    ├── .env.example
    ├── agent.py
    ├── log_tools.py
    ├── requirements.txt
    └── lib/
        ├── __init__.py
        └── redis_memory_service.py
```

- `adk_cli.py`: A custom command-line interface script that registers the Redis memory service with the ADK.
- `redis_memory_service/`: The main application directory containing the agent definition and supporting files.
- `redis_memory_service/agent.py`: Defines the simple QA agent.
- `redis_memory_service/requirements.txt`: Lists the Python dependencies for the project.
- `notebooks/`: Contains a Jupyter notebook for an interactive walkthrough of the service.

## Prerequisites

To run this agent, you will need:
- A terminal
- Git
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A running [Redis](https://redis.io/docs/getting-started/installation/) instance.

## Run Locally

1.  **Clone this repository** and navigate to this subdirectory.

2.  **Set up environment variables**:

    Copy the `.env.example` file to `.env` and fill in your Google Cloud project details.

    ```bash
    cp redis_memory_service/.env.example redis_memory_service/.env
    ```

    Your `redis_memory_service/.env` file should look like this:

    ```
    GOOGLE_GENAI_USE_VERTEXAI=1
    GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    GOOGLE_CLOUD_LOCATION="your-gcp-location (e.g., us-central1)"
    ```

3.  **Install dependencies**:

    Create a virtual environment and install the required packages.

    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install -r redis_memory_service/requirements.txt
    ```

4.  **Run the ADK web UI**:

    Start the ADK web server, pointing to the agent directory and specifying the Redis session service URI. The `adk_cli.py` script ensures that the `redis://` protocol is recognized.

    ```bash
    uv run python adk_cli.py web \
        --memory_service_uri="redis://localhost:6379?index_name=memory&embedding_model_name=gemini-embedding-001&similarity_top_k=10&ttl=86400" \
        redis_memory_service
    ```

    *   `--memory_service_uri`: The URI for the `RedisMemoryService`. Query parameters can be used to configure the service:
        *   `index_name`: The name of the Redis search index (default: `memory`).
        *   `embedding_model_name`: The name of the embedding model to use (default: `gemini-embedding-001`).
        *   `similarity_top_k`: The number of contexts to retrieve during a search (default: `10`).
        *   `ttl`: The time-to-live for memory entries in Redis, in seconds (default: `86400` seconds, i.e., 24 hours).

    Navigate to `127.0.0.1:8000` in your browser to interact with the agent.

## Inspecting Session Data

As you interact with the agent, its long-term memories will be stored in your Redis database. You can inspect this data using the `redis-cli`.

1.  **Connect to Redis**:
    ```bash
    redis-cli
    ```

2.  **List all RediSearch indexes**:
    Use `FT._LIST` to see all active RediSearch indexes. This will show the `index_name` you configured (e.g., `memory`).
    ```bash
    FT._LIST
    ```

3.  **Get information about a specific index**:
    Use `FT.INFO <index_name>` to get detailed information about your memory index.
    ```bash
    FT.INFO memory
    ```

4.  **Find stored keys using SCAN**:
    To find the keys stored for your memories, use the `SCAN` command with a `MATCH` pattern based on your `index_name`. This is safer than `KEYS` for production environments.
    ```bash
    SCAN 0 MATCH memory:* COUNT 10
    ```
    (Replace `memory` with your configured `index_name` if different.)

5.  **Get the data for a specific memory**:
    Once you have a key (e.g., `memory:some_hash_id`), you can retrieve its content using `HGETALL`.
    ```bash
    HGETALL "<index_name>:<hash_id>"
    ```
    This will return the JSON object containing the memory entry, including the embedded content and metadata.

## Deploying to Cloud Run

You can deploy the agent to Cloud Run for a scalable setup. This requires a Redis instance accessible from your Cloud Run service.

### 1. Prepare Redis

Before deploying, you need a Redis instance. For production, it's recommended to use a managed service like [Google Cloud Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis).

- Create a Memorystore for Redis instance within the same VPC network you plan to use for Cloud Run.
- Once created, note its IP address and port. Your Redis URI will be `redis://<redis_ip_address>:<redis_port>`.

### 2. Deploy the Agent

- **Authenticate with Google Cloud**:
    ```bash
    gcloud auth login
    ```
- **Set Environment Variables**:
    ```bash
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    # The Redis instance must be accessible from this VPC
    export VPC_NETWORK="your-vpc-network"
    export VPC_SUBNET="your-private-subnet-for-redis"
    # The Redis URI from the previous step
    export REDIS_URI="redis://<your-redis-ip>:<your-redis-port>"
    ```
- **Run the Deployment Script**:
    From the project root directory (`./my-adk-python-samples`), run the following command. The script handles containerization and deployment. The `--run-command` argument is used to start the ADK server with the correct Redis session URI.
    ```bash
    python deploy_to_cloud_run.py --agent-folder=agent-memory/redis-session-service/redis_session_service \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$GOOGLE_CLOUD_LOCATION \
        --service-name="redis-memory-agent" \
        --vpc-egress="all-traffic" \
        --network=$VPC_NETWORK \
        --subnet=$VPC_SUBNET \
        --with-ui \
        --allow-unauthenticated \
        --log-level DEBUG \
        --adk-cli-path=agent-memory/redis-memory-service/adk_cli.py \
        --session-service-uri="$REDIS_URI" \
        --memory-service-uri="$REDIS_URI"
    ```
- The `--vpc-egress` flag configures the necessary Serverless VPC Access Connector so the agent can communicate with the Redis instance on your VPC.
- Once complete, the script will provide a public URL to access your agent.

## References

- [(adk-python) Support to configure Redis as the session storage](https://github.com/google/adk-python/issues/938#issuecomment-3429871364)
- [ADK Python Community Contributions](https://github.com/google/adk-python-community)
- 📓 [Get started with Memory Bank on ADK](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/memory_bank/get_started_with_memory_bank_on_adk.ipynb)
- 🎥 [How to build AI agents with memory](https://youtu.be/sMtrelDNxIc?si=sw_-ALjIP93DjtED)
- [Remember this: Agent state and memory with ADK (2025-08-02)](https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk?hl=en)
- 📦 [Redis Agent Memory Server](https://github.com/redis/agent-memory-server): A memory layer for AI agents using Redis as the vector database.
