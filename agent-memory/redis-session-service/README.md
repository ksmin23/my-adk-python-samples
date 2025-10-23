# ADK Redis Session Service Example

This project contains a sample agent built with [ADK Python](https://google.github.io/adk-docs/) that demonstrates how to use Redis for session state management.

This sample agent shows how you can integrate a custom session service with the ADK to persist conversation state in a Redis database. This allows for scalable and persistent user sessions.

---

## Directory Structure

The project is organized as follows:

```
./redis-session-service
├── adk_cli.py
├── README.md
├── notebooks
│   └── get_started_with_adk_redis_session_service.ipynb
└── redis_session_service
    ├── __init__.py
    ├── agent.py
    ├── log_tools.py
    ├── requirements.txt
    └── .env.example
```

- `adk_cli.py`: A custom command-line interface script that registers the Redis session service with the ADK.
- `redis_session_service/`: The main application directory containing the agent definition and supporting files.
- `redis_session_service/agent.py`: Defines the simple QA agent.
- `redis_session_service/requirements.txt`: Lists the Python dependencies for the project.
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
    cp redis_session_service/.env.example redis_session_service/.env
    ```

    Your `redis_session_service/.env` file should look like this:

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
    uv pip install -r redis_session_service/requirements.txt
    ```

4.  **Run the ADK web UI**:

    Start the ADK web server, pointing to the agent directory and specifying the Redis session service URI. The `adk_cli.py` script ensures that the `redis://` protocol is recognized.

    ```bash
    uv run python adk_cli.py web --agents_dir=./redis_session_service --session_service_uri="redis://localhost:6379"
    ```

    Navigate to `127.0.0.1:8000` in your browser to interact with the agent.

## Inspecting Session Data

As you interact with the agent, its session state will be stored in your Redis database. You can inspect this data using the `redis-cli`.

1.  **Connect to Redis**:
    ```bash
    redis-cli
    ```

2.  **List all keys** to find the session IDs:
    ```
    KEYS "session:*"
    ```

3.  **Get the data for a specific session**:
    Replace `<session_id>` with an ID from the previous step.
    ```
    GET "session:<session_id>"
    ```

This will return a JSON object containing the session state, including the conversation history.

## References

- [(adk-python) Support to configure Redis as the session storage](https://github.com/google/adk-python/issues/938#issuecomment-3429871364)
- [ADK Python Community Contributions](https://github.com/google/adk-python-community)
