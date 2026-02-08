# BigQuery Data Agent with Agent Engine Memory Bank

A self-learning BigQuery agent that stores and retrieves successful SQL queries using the Agent Engine Memory Bank. Queries can be shared across users within a team or kept private.

## Features

- **Natural Language to SQL**: Convert user questions to BigQuery SQL.
- **Self-Learning Memory**: Automatically searches past queries before generating new ones.
- **Scoped Sharing**: Save queries to personal (`user`) or shared (`team`) memory.
- **Enhanced Searchability**: Each saved query includes title, description, and original question for accurate retrieval.
- **Built-in Memory Tools**:
    - `PreloadMemoryTool`: Automatically retrieves relevant memories into system instructions.
    - `LoadMemoryTool`: Allows the agent to selectively load specific memories when needed.

## Prerequisites

- Python 3.10+
- Google Cloud Project with:
  - BigQuery API enabled
  - Vertex AI API enabled (for Agent Engine Memory Bank)
- ADK installed (`pip install google-adk`)
- Vertex AI SDK (`pip install google-cloud-aiplatform`)

## Setup

### 1. Configure Environment

Create a `.env` file in `bigquery_data_agent/`:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# BigQuery Configuration
BIGQUERY_DATASET=your_dataset_name

# Agent Configuration
AGENT_MODEL=gemini-2.5-flash

# Agent Engine Memory Bank (required for query storage)
AGENT_ENGINE_ID=your-agent-engine-id
```

### 2. Create Memory Bank

Before running the agent, create an Agent Engine with Memory Bank configuration:

```bash
python utils/setup_memory_bank.py --project=your-project-id --location=us-central1
```

This creates an Agent Engine with custom memory topics for scope-based SQL query storage.
Copy the output `AGENT_ENGINE_ID` to your `.env` file.

### 3. Run the Agent

```bash
# From this directory
adk web
```

Or programmatically:

```python
from bigquery_data_agent.agent import root_agent
# ... use with Runner
```

## Test Scenarios

### Scenario 1: Save a User-Scope Query

```
User: "월별 매출 합계를 보여줘"
Agent: (executes query and returns results)
User: "이 쿼리를 저장해줘. 제목은 '월별 매출 합계'로 해줘."
Agent: "Query '월별 매출 합계' saved to user memory."
```

### Scenario 2: Save a Team-Scope Query

```
User: "Top 10 고객 목록을 팀 공유로 저장해줘"
Agent: "Query 'Top 10 Customers' saved to team memory."
```

### Scenario 3: Search Existing Queries

```
User: "매출 관련 쿼리 찾아줘"
Agent: (searches user and team memories)
       "Found 2 matches:
        1. [user] 월별 매출 합계 - 최근 12개월의 월별 매출 합계
        2. [team] 일별 매출 리포트 - 일별 매출 현황 조회"
```

### Scenario 4: Scope Isolation Test

```
# User A saves to user scope
User A: "이 쿼리를 내 개인 저장소에 저장해줘"

# User B should NOT see User A's personal queries
User B: "내 저장된 쿼리 검색해줘"
Agent: (returns only User B's personal queries)
```

## Project Structure

```
bigquery-data-agent/
├── README.md
├── utils/                   # Utility and configuration scripts
│   ├── __init__.py
│   ├── memory_config.py     # Memory Bank configuration
│   └── setup_memory_bank.py  # CLI script to create Agent Engine
└── bigquery_data_agent/
    ├── __init__.py
    ├── .env.example          # Environment configuration template
    ├── agent.py              # LlmAgent definition
    ├── prompts.py            # Agent instructions
    └── tools.py              # BigQuery and Memory tools
```

## Memory Storage Format

Queries are stored with the following structure:

```
Title: 월별 매출 합계
Description: 최근 12개월의 월별 매출 합계를 조회합니다. 매출 트렌드 분석에 사용합니다.
NL Query: 월별 매출 합계를 보여줘
SQL: SELECT FORMAT_DATE('%Y-%m', order_date) AS month, SUM(amount) AS total_sales ...
```

## Scope Types

| Scope | Storage | Visibility |
|-------|---------|------------|
| `user` | user_id | Personal only |
| `team` | team_id | All team members |
| `global` | (search only) | Searches both user and team |
