# BigQuery Data Agent with Agent Engine Memory Bank

This project demonstrates a self-learning BigQuery agent built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that leverages the [Vertex AI Agent Engine Memory Bank](https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/overview).

The agent can convert natural language questions into BigQuery SQL queries and execute them. More importantly, it can **learn** from its interactions by saving successful queries to a long-term memory store. This memory is **scoped**, allowing queries to be private to a user or shared across a team, enabling detailed personalization and knowledge sharing.

## Features

- **Natural Language to SQL**: Converts user questions into syntactically correct BigQuery SQL.
- **Dynamic Context**: Automatically searches for relevant past queries to improve accuracy and efficiency.
- **Scoped Memory**:
    - `user`: Queries are private to the individual user.
    - `team`: Queries are shared with all members of a specific team.
- **Enhanced Searchability**: Stored queries include the original question, SQL, title, and description for accurate retrieval.
- **Built-in Memory Tools**:
    - `PreloadMemoryTool`: Automatically injecting relevant memories into the agent's context.
    - `LoadMemoryTool`: Enabling the agent to explicitly retrieve memories when needed.

## Architecture

### System Architecture

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "transparent",
    "primaryTextColor": "#202124",
    "primaryBorderColor": "#1A73E8",
    "secondaryColor": "transparent",
    "secondaryTextColor": "#202124",
    "secondaryBorderColor": "#1E8E3E",
    "tertiaryColor": "transparent",
    "tertiaryTextColor": "#202124",
    "tertiaryBorderColor": "#F9AB00",
    "lineColor": "#5F6368",
    "textColor": "#202124",
    "fontSize": "14px"
  }
}}%%

flowchart TB
    %% ── User ──
    User["👤 User<br/>(Natural Language Query)"]

    %% ── ADK Runtime ──
    subgraph ADK["<b>Google ADK Runtime</b>"]
        direction TB

        subgraph AgentCore["<b>Root Agent: bigquery_data_agent</b><br/>Model: Gemini 2.5 Flash | Temperature: 0.01"]
            direction TB
            Instruction["📋 System Instruction<br/>(prompts.py)<br/>• Decision Flow<br/>• Query Execution Workflow<br/>• Memory Scope Rules<br/>• Global SQL Rules"]
        end

        subgraph Callbacks["<b>Callbacks</b>"]
            direction LR
            AfterTool["🔄 after_tool_callback<br/><i>store_query_result_in_state</i><br/>━━━━━━━━━━━━━━━<br/>Caches last SQL, results,<br/>dataset_id in session state"]
            AfterAgent["💾 after_agent_callback<br/><i>auto_save_session_to_memory</i><br/>━━━━━━━━━━━━━━━<br/>Saves session to Memory Bank<br/>after each interaction"]
        end

        subgraph Tools["<b>Agent Tools</b>"]
            direction TB

            subgraph BQTools["BigQuery Tools"]
                BQToolset["🔍 BigQueryToolset<br/>(execute_sql)<br/>━━━━━━━━━━━━━<br/>WriteMode: BLOCKED<br/>(SELECT only)"]
            end

            subgraph MemTools["Memory Tools"]
                direction TB
                SearchHistory["🔎 search_query_history<br/>━━━━━━━━━━━━━<br/>Scope: user / team / global<br/>Similarity search + metadata filter"]
                SaveQuery["💾 save_query_to_memory<br/>━━━━━━━━━━━━━<br/>Scope: user / team<br/>Structured fact storage"]
                SetUserProp["👤 set_user_property<br/>━━━━━━━━━━━━━<br/>Store persistent user props<br/>(e.g., team_id)"]
            end

            subgraph ADKMemTools["ADK Built-in Memory Tools"]
                PreloadMem["📥 preload_memory_tool<br/>Auto-load relevant memories"]
                LoadMem["📤 load_memory_tool<br/>Selective memory retrieval"]
            end
        end
    end

    %% ── External Services ──
    subgraph GCP["<b>Google Cloud Platform</b>"]
        direction TB

        BQ[("🗄️ BigQuery<br/>━━━━━━━━━━━<br/>Project / Dataset<br/>(Read-only access)")]

        subgraph AgentEngine["<b>Vertex AI Agent Engine</b><br/>(Memory Bank)"]
            direction TB

            subgraph MemScopes["Memory Scopes"]
                direction LR
                UserScope["👤 User Scope<br/>(user_id)<br/>━━━━━━━━━━━━━<br/>• Personal SQL queries<br/>• User profile (team_id, etc.)<br/>• Preferences<br/>• Conversation details"]
                TeamScope["👥 Team Scope<br/>(team_id)<br/>━━━━━━━━━━━━━<br/>• Shared SQL queries<br/>• Team preferences<br/>• Key details"]
            end

            MemConfig["⚙️ Customization Config<br/>━━━━━━━━━━━━━<br/>• Custom Topic: sql_query<br/>• Managed Topics:<br/>  USER_PERSONAL_INFO,<br/>  USER_PREFERENCES,<br/>  KEY_CONVERSATION_DETAILS,<br/>  EXPLICIT_INSTRUCTIONS<br/>• Few-shot examples"]
        end
    end

    %% ── Setup Utilities ──
    subgraph SetupUtils["<b>Setup Utilities</b> (utils/)"]
        direction LR
        SetupScript["🛠️ setup_memory_bank.py<br/>CLI: create / update<br/>Agent Engine"]
        CustomConfig["📝 memory_bank_customization.py<br/>CustomizationConfig builder<br/>for user & team scopes"]
    end

    %% ── Connections ──
    User -->|"NL Query"| AgentCore
    AgentCore -->|"Response<br/>(Markdown + SQL)"| User

    AgentCore --> Tools
    AgentCore --> Callbacks

    BQToolset -->|"SQL Query"| BQ
    BQ -->|"Query Results"| BQToolset

    AfterTool -.->|"Update session state"| AgentCore
    AfterAgent -.->|"memory_service.add_session_to_memory()"| AgentEngine

    SearchHistory -->|"memories.retrieve()<br/>similarity_search"| AgentEngine
    SaveQuery -->|"memories.generate()<br/>direct_memories"| AgentEngine
    SetUserProp -->|"memories.generate()<br/>(profile metadata)"| AgentEngine
    PreloadMem -.->|"Auto-retrieve"| AgentEngine
    LoadMem -.->|"On-demand retrieve"| AgentEngine

    SetupScript --> CustomConfig
    CustomConfig -->|"agent_engines.create()<br/>agent_engines.update()"| AgentEngine

    %% ── Styling ──
    classDef userStyle fill:none,stroke:#1A73E8,stroke-width:2px,color:#1A73E8
    classDef agentStyle fill:none,stroke:#1E8E3E,stroke-width:2px,color:#1E8E3E
    classDef toolStyle fill:none,stroke:#F9AB00,stroke-width:1.5px,color:#E37400
    classDef gcpStyle fill:none,stroke:#9334E6,stroke-width:2px,color:#7627BB
    classDef memStyle fill:none,stroke:#D93025,stroke-width:1.5px,color:#C5221F
    classDef setupStyle fill:none,stroke:#5F6368,stroke-width:1.5px,color:#3C4043
    classDef callbackStyle fill:none,stroke:#3F51B5,stroke-width:1.5px,color:#283593

    class User userStyle
    class AgentCore,Instruction agentStyle
    class BQToolset,SearchHistory,SaveQuery,SetUserProp,PreloadMem,LoadMem toolStyle
    class BQ gcpStyle
    class UserScope,TeamScope,MemConfig memStyle
    class SetupScript,CustomConfig setupStyle
    class AfterTool,AfterAgent callbackStyle
```

### Query Execution Flow

```mermaid
sequenceDiagram
    actor User
    participant Agent as bigquery_data_agent<br/>(Gemini 2.5 Flash)
    participant State as Session State
    participant MB as Memory Bank<br/>(Agent Engine)
    participant BQ as BigQuery

    Note over User, BQ: 1. User asks a natural language question

    User ->> Agent: NL Query (e.g., "Show top search terms in NYC")

    Note over Agent, MB: 2. preload_memory_tool auto-injects relevant memories
    Agent -) MB: preload_memory_tool()
    MB --) Agent: Relevant memories (if any)

    Note over Agent, MB: 3. MANDATORY: Search for similar past queries
    Agent ->> MB: search_query_history(nl_query, scope="global")
    MB ->> MB: similarity_search + metadata filter<br/>(content_type = "sql")
    MB -->> Agent: Matching queries (0..N)

    alt Memory HIT — Similar query found
        Note over Agent: Reuse saved SQL<br/>(directly or as template)
    else Memory MISS — No match
        Note over Agent: Generate new SQL from<br/>schema + NL query
    end

    Note over Agent, BQ: 4. Execute SQL against BigQuery
    Agent ->> BQ: execute_sql(sql)
    BQ -->> Agent: Query results (rows)

    Note over Agent, State: 5. after_tool_callback fires
    Agent ->> State: store_query_result_in_state()<br/>• last_executed_query<br/>• last_query_results<br/>• last_dataset_id

    Note over User, Agent: 6. Return results to user
    Agent -->> User: Markdown response<br/>(SQL + results table)

    Note over User, MB: 7. Ask to save & persist (if new query)
    Agent -->> User: "Save this query to memory?<br/>(Scope: User / Team)"

    alt User agrees to save
        User ->> Agent: "Save as 'NYC Top Terms' to team"

        opt team scope & no team_id
            Agent ->> MB: get_team_id_from_user_memory()
            MB -->> Agent: team_id
        end

        Agent ->> MB: save_query_to_memory()<br/>Title, Description, NL Query, SQL
        MB -->> Agent: ✓ Saved (scope=user|team)
        Agent -->> User: "Query saved to memory."
    end

    Note over Agent, MB: 8. after_agent_callback fires
    Agent -) MB: auto_save_session_to_memory()<br/>memory_service.add_session_to_memory()
```

### Memory Scopes

| Scope | Identifier | Visibility | Usage |
| :--- | :--- | :--- | :--- |
| **`user`** | `user_id` | **Private** | Personal analysis, ad-hoc queries |
| **`team`** | `team_id` | **Shared** | Standard reports, team dashboards, common metrics |
| **`global`** | N/A | **Public** | (Implementation dependent) Organization-wide KPIs |

### Memory Storage Structure

Saved memories are structured to maximize retrieval accuracy:

```text
Title: Monthly Sales Report
Description: Aggregates sales data by month for the last 12 months.
NL Query: Show me monthly sales trends
SQL: SELECT FORMAT_DATE('%Y-%m', date) as month, SUM(amount) FROM ...
```

## Directory Structure

The project is organized as follows:

```
bigquery-data-agent-with-dynamic-context/
├── README.md
├── utils/
│   ├── __init__.py
│   ├── memory_bank_customization.py  # Configuration for Memory Bank topics
│   └── setup_memory_bank.py          # Script to provision the Agent Engine
└── bigquery_data_agent/
    ├── __init__.py
    ├── .env.example                  # Template for environment variables
    ├── agent.py                      # Main agent definition and callbacks
    ├── log_tools.py                  # Logging utilities
    ├── prompts.py                    # System instructions and prompt templates
    ├── requirements.txt              # Project dependencies
    └── tools.py                      # Tool implementations (BigQuery, Memory)
```

- `bigquery_data_agent/agent.py`: Defines the `LlmAgent`, including model configuration and tool registration.
- `bigquery_data_agent/log_tools.py`: Helper functions for logging system instructions and tool calls.
- `bigquery_data_agent/prompts.py`: Contains the system instructions and prompt templates for the agent.
- `bigquery_data_agent/tools.py`: Implements the core logic for executing SQL, saving queries to memory, and searching history.
- `utils/memory_bank_customization.py`: Defines the Memory Bank configuration, including custom topics like `sql_query`.
- `utils/setup_memory_bank.py`: A utility script to initialize the Vertex AI Agent Engine and Memory Bank.

## Prerequisites

To run this agent, you will need:

- **Python 3.10+**
- **Google Cloud Project** with the following APIs enabled:
    - BigQuery API (`bigquery.googleapis.com`)
    - Vertex AI API (`aiplatform.googleapis.com`)
    - Agent Engine API (if applicable for your region)
- **ADK** installed (`pip install google-adk`)
- **Vertex AI SDK** (`pip install google-cloud-aiplatform`)

## Setup

### 1. Installation

Clone the repository and install the dependencies:

```bash
# Navigate to the project directory
cd agents/agent-memory/bigquery-data-agent-with-dynamic-context

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (assuming adk and other libs are in requirements.txt or installed manually)
pip install google-adk google-cloud-aiplatform python-dotenv
```

### 2. Configuration

Create a `.env` file in the `bigquery_data_agent/` directory:

```bash
cp bigquery_data_agent/.env.example bigquery_data_agent/.env
```

Edit the `.env` file with your project details:

```ini
# Google Cloud Configuration
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# (Optional) BigQuery Configuration
BIGQUERY_DATASET=your_dataset_name

# Agent Configuration
AGENT_MODEL=gemini-2.5-flash
```

### 3. Provision Memory Bank

Before running the agent for the first time, you must provision the Agent Engine Memory Bank. This script creates the necessary resources on Vertex AI.

```bash
python utils/setup_memory_bank.py --project=your-project-id --location=us-central1
```

This will create an Agent Engine named `bigquery_data_agent` (matching the agent's name in `agent.py`). The ADK framework automatically connects to this engine at runtime.

## Running the Agent

You can run the agent using the ADK CLI web server:

```bash
adk web bigquery_data_agent
```

Then open your browser to the URL provided (usually `http://127.0.0.1:8000`).

## Demo Walkthrough

### 1. Natural Language to SQL & Context Saving
In this first session, the user asks a question about Google Trends data. The agent generates the SQL, executes it, and then saves the successful query to memory for future use.

![Session 1 - Query Execution](./assets/bq-data-agent-with-dynamic-context-1a.png)
![Session 1 - Saving to Memory](./assets/bq-data-agent-with-dynamic-context-1b.png)

### 2. Retrieving from Memory in a New Session
In a subsequent session, the user asks a similar question. The agent recognizes the intent, retrieves the saved query from the Memory Bank, and executes it immediately without needing to regenerate the SQL.

![Session 2 - Query Retrieval](./assets/bq-data-agent-with-dynamic-context-2.png)

### 3. Agent Engine Memory Bank view
The saved queries are stored as structured memories in the Agent Engine, visible in the Google Cloud Console.

![Agent Memory Bank](./assets/bq-data-agent-memory_bank.png)

## Usage Examples

### Scenario 1: Natural Language to SQL

**User**: "Using bigquery-public-data.google_trends dataset, what are the top 20 most popular search terms last week in NYC based on rank?"

**Agent**:
1.  Searches memory for similar past queries (none found).
2.  Generates and executes the BigQuery SQL.
3.  Returns the results.
4.  Asks if you want to save this query.

### Scenario 2: Saving to User Memory

**User**: "Save this query as 'NYC Top Search Terms' to my private memory."

**Agent**: Saves the query with scope `user`. Only you will be able to retrieve this query in future sessions.

### Scenario 3: Saving to Team Memory

**User**: "Save this query as 'Weekly Trend Report' for the team."

**Agent**: Requires a `team_id` (e.g., "data-science"). Saves the query with scope `team`. All members of "data-science" can now access this query.

### Scenario 4: Retrieving from Memory

**User**: "What were the top search terms in NYC?"

**Agent**:
1.  Searches memory and finds the "NYC Top Search Terms" query.
2.  Uses the saved SQL as a starting point.
3.  Executes the query and returns the answer immediately, without needing to regenerate the SQL from scratch.

## 💡 Future Works

- **Template-based Query Storage**: Store queries as parameterized templates (e.g., `WHERE date = @date`) to improve reusability across different time ranges and conditions.
- **Automated Golden Query Generation**: Analyze BigQuery execution history in batch to identify high-value, frequently used queries ("Golden Queries") and automatically populate the Memory Bank.
- **Business Context Extraction**: Automatically extract and store business logic and definitions from query comments and usage patterns to enhance the agent's domain understanding.

## References

- 📓 [Get started with Memory Bank on ADK](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/memory_bank/get_started_with_memory_bank_on_adk.ipynb)
- 📝 [Self Improving Text2Sql Agent with Dynamic Context](https://www.ashpreetbedi.com/articles/sql-agent)
- :octocat: [Dash - Self-learning Data Agent](https://github.com/agno-agi/dash)
- 📝 [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)
- [Gemini for Google Cloud > Conversational Analytics API: Build data agents and chat with your data](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/overview)
  - [Google Codelabs: Introduction to the Conversational Analytics API](https://codelabs.developers.google.com/ca-api-bigquery#0)
  - :octocat: [Intro to Gemini Data Analytics](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/gemini_data_analytics/intro_gemini_data_analytics_sdk.ipynb)