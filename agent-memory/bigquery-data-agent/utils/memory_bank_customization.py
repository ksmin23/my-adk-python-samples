#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Memory Bank customization configuration for BigQuery Data Agent."""

import os

import vertexai
from google.genai.types import Content, Part
from vertexai import types

# Note: vertexai.types is a lazy-loaded property, not a physical module.
# Using 'from vertexai.types import ...' would fail with ModuleNotFoundError.
# Instead, we import 'types' from 'vertexai' to trigger the lazy-loading mechanism.

CustomizationConfig = types.MemoryBankCustomizationConfig
MemoryTopic = types.MemoryBankCustomizationConfigMemoryTopic
CustomMemoryTopic = types.MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic
GenerateMemoriesExample = types.MemoryBankCustomizationConfigGenerateMemoriesExample
ConversationSource = (
  types.MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource
)
ConversationSourceEvent = (
  types.MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent
)
ExampleGeneratedMemory = (
  types.MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory
)
ManagedMemoryTopic = types.MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic
ManagedTopicEnum = types.ManagedTopicEnum

# Custom Memory Topic for SQL queries
SQL_QUERY_TOPIC = CustomMemoryTopic(
  label="sql_query",
  description="""Validated BigQuery SQL queries that successfully answered 
  user questions. Each memory includes title, description, natural language question, 
  and corresponding SQL query for future reuse.""",
)


def create_example_memories() -> list[GenerateMemoriesExample]:
  """Create few-shot examples for memory extraction.

  Returns:
    A list of GenerateMemoriesExample objects.
  """
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
            parts=[
              Part(
                text="""SQL executed:
```sql
SELECT 
  FORMAT_DATE('%Y-%m', order_date) AS month,
  SUM(amount) AS total_sales
FROM `project.dataset.orders`
GROUP BY month
ORDER BY month DESC
LIMIT 12
```
Result: Total sales by month for the last 12 months."""
              )
            ],
          )
        ),
        ConversationSourceEvent(
          content=Content(
            role="user",
            parts=[
              Part(
                text="Save this query. Set the title to 'Monthly Sales Summary'."
              )
            ],
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
  """Get CustomizationConfig for user-scoped memories.

  Returns:
    A CustomizationConfig object for user scope.
  """
  return CustomizationConfig(
    scope_keys=["user_id"],
    memory_topics=[
      MemoryTopic(custom_memory_topic=SQL_QUERY_TOPIC),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS
        )
      ),
    ],
    generate_memories_examples=create_example_memories(),
  )


def get_team_scope_config() -> CustomizationConfig:
  """Get CustomizationConfig for team-scoped memories.

  Returns:
    A CustomizationConfig object for team scope.
  """
  return CustomizationConfig(
    scope_keys=["team_id"],
    memory_topics=[
      MemoryTopic(custom_memory_topic=SQL_QUERY_TOPIC),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS
        )
      ),
      MemoryTopic(
        managed_memory_topic=ManagedMemoryTopic(
          managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS
        )
      ),
    ],
    generate_memories_examples=create_example_memories(),
  )


def create_agent_engine_with_memory_bank(
  project: str,
  location: str,
  display_name: str = "bigquery_data_agent",
) -> str:
  """Create Agent Engine with Memory Bank CustomizationConfig.

  Args:
    project: Google Cloud Project ID.
    location: Google Cloud Location.
    display_name: The display name for the Agent Engine.

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
      },
    }
  )

  return agent_engine.api_resource.name.split("/")[-1]


def update_agent_engine_memory_config(
  agent_engine_id: str,
  project: str,
  location: str,
) -> None:
  """Update existing Agent Engine with Memory Bank CustomizationConfig.

  Args:
    agent_engine_id: Existing Agent Engine ID to update.
    project: Google Cloud Project ID.
    location: Google Cloud Location.
  """
  client = vertexai.Client(project=project, location=location)
  agent_engine_name = (
    f"projects/{project}/locations/{location}/reasoningEngines/{agent_engine_id}"
  )

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
