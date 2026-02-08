"""Memory Bank configuration for BigQuery Data Agent."""
import os
import vertexai
from vertexai.types import (
    MemoryBankCustomizationConfig as CustomizationConfig,
    MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic as CustomMemoryTopic,
    MemoryBankCustomizationConfigGenerateMemoriesExample as GenerateMemoriesExample,
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource as ConversationSource,
    MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent as ConversationSourceEvent,
    MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory as ExampleGeneratedMemory,
    MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic as ManagedMemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopicManagedTopicEnum as ManagedTopicEnum,
)
from google.genai.types import Content, Part


# Custom Memory Topic for SQL queries
SQL_QUERY_TOPIC = CustomMemoryTopic(
    label="sql_query",
    description="""Validated BigQuery SQL queries that successfully answered 
    user questions. Each memory includes title, description, natural language question, 
    and corresponding SQL query for future reuse.""",
)

def create_example_memories() -> list[GenerateMemoriesExample]:
    """Create few-shot examples for memory extraction."""
    # Example 1: Successful query storage
    example_save = GenerateMemoriesExample(
        conversation_source=ConversationSource(
            events=[
                ConversationSourceEvent(
                    content=Content(
                        role="user",
                        parts=[Part(text="Show me total sales by month")],
                    )
                ),
                ConversationSourceEvent(
                    content=Content(
                        role="model",
                        parts=[Part(text="""SQL executed:
```sql
SELECT 
  FORMAT_DATE('%Y-%m', order_date) AS month,
  SUM(amount) AS total_sales
FROM `project.dataset.orders`
GROUP BY month
ORDER BY month DESC
LIMIT 12
```
Result: Total sales by month for the last 12 months.""")],
                    )
                ),
                ConversationSourceEvent(
                    content=Content(
                        role="user",
                        parts=[Part(text="Save this query. Set the title to 'Monthly Sales Summary'.")],
                    )
                ),
            ]
        ),
        generated_memories=[
            ExampleGeneratedMemory(
                fact="""Title: Monthly Sales Summary
Description: Retrieves the total sales by month for the last 12 months. Used for sales trend analysis.
NL Query: Show me total sales by month
SQL: SELECT FORMAT_DATE('%Y-%m', order_date) AS month, SUM(amount) AS total_sales FROM `project.dataset.orders` GROUP BY month ORDER BY month DESC LIMIT 12"""
            ),
        ],
    )

    # Example 2: No-op case (not a save request)
    noop_example = GenerateMemoriesExample(
        conversation_source=ConversationSource(
            events=[
                ConversationSourceEvent(
                    content=Content(
                        role="user",
                        parts=[Part(text="What is today's date?")],
                    )
                ),
                ConversationSourceEvent(
                    content=Content(
                        role="model",
                        parts=[Part(text="Today is February 6, 2025.")],
                    )
                ),
            ]
        ),
        generated_memories=[],  # No memories should be generated
    )

    return [example_save, noop_example]


def get_user_scope_config() -> CustomizationConfig:
    """Get CustomizationConfig for user-scoped memories."""
    return CustomizationConfig(
        scope_keys=["user_id"],
        memory_topics=[
            MemoryTopic(custom_memory_topic=SQL_QUERY_TOPIC),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS)),
        ],
        generate_memories_examples=create_example_memories(),
    )


def get_team_scope_config() -> CustomizationConfig:
    """Get CustomizationConfig for team-scoped memories."""
    return CustomizationConfig(
        scope_keys=["team_id"],
        memory_topics=[
            MemoryTopic(custom_memory_topic=SQL_QUERY_TOPIC),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS)),
            MemoryTopic(managed_memory_topic=ManagedMemoryTopic(managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS)),
        ],
        generate_memories_examples=create_example_memories(),
    )


def create_agent_engine_with_memory_bank(
    project: str,
    location: str,
    display_name: str = "bigquery-data-agent",
) -> str:
    """Create Agent Engine with Memory Bank CustomizationConfig.
    
    Returns:
        Agent Engine ID (last segment of the resource name).
    """
    client = vertexai.Client(project=project, location=location)
    
    agent_engine = client.agent_engines.create(
        config={
            "display_name": display_name,
            "context_spec": {
                "memory_bank_config": {
                    "generation_config": {
                        "model": f"projects/{project}/locations/{location}/publishers/google/models/gemini-2.5-flash"
                    },
                    "customization_configs": [
                        get_user_scope_config(),
                        get_team_scope_config(),
                    ],
                }
            }
        }
    )

    return agent_engine.api_resource.name.split("/")[-1]


def update_agent_engine_memory_config(
    agent_engine_id: str,
    project: str,
    location: str,
) -> None:
    """Update existing Agent Engine with Memory Bank CustomizationConfig."""
    client = vertexai.Client(project=project, location=location)
    agent_engine_name = f"projects/{project}/locations/{location}/reasoningEngines/{agent_engine_id}"
    
    client.agent_engines.update(
        name=agent_engine_name,
        config={
            "context_spec": {
                "memory_bank_config": {
                    "customization_configs": [
                        get_user_scope_config(),
                        get_team_scope_config(),
                    ],
                }
            }
        },
    )
