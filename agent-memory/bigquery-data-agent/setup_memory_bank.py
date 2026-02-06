#!/usr/bin/env python3
"""CLI script to setup Agent Engine with Memory Bank for BigQuery Data Agent.

This script creates an Agent Engine with Memory Bank configuration
including custom topics for SQL query storage with scope-based isolation.

Usage:
  python setup_memory_bank.py --project=your-project-id --location=us-central1

After setup, add the AGENT_ENGINE_ID to your .env file.
"""

import argparse
import logging
import os
import sys

import vertexai
from google.genai.types import Content, Part
from vertexai.types import MemoryBankCustomizationConfig as CustomizationConfig
from vertexai.types import (
  MemoryBankCustomizationConfigGenerateMemoriesExample as GenerateMemoriesExample,
)
from vertexai.types import (
  MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource as ConversationSource,
)
from vertexai.types import (
  MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent as ConversationSourceEvent,
)
from vertexai.types import (
  MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory as ExampleGeneratedMemory,
)
from vertexai.types import MemoryBankCustomizationConfigMemoryTopic as MemoryTopic
from vertexai.types import (
  MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic as CustomMemoryTopic,
)

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_sql_query_topic() -> MemoryTopic:
  """Create a custom memory topic for SQL queries."""
  return MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
      label="sql_query",
      description="""Validated BigQuery SQL queries that successfully answered 
user questions. Each memory includes:
- Title: A concise name for the query (e.g., "Monthly Sales Summary")
- Description: What the query does and when to use it
- SQL: The actual BigQuery SQL query
- NL Query: The original natural language question

Only store queries that were validated and confirmed by the user.""",
    )
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


def create_customization_configs() -> list[CustomizationConfig]:
  """Create CustomizationConfigs for user and team scopes."""
  sql_query_topic = create_sql_query_topic()
  examples = create_example_memories()

  # User scope: Personal queries
  user_config = CustomizationConfig(
    scope_keys=["user_id"],
    memory_topics=[sql_query_topic],
    generate_memories_examples=examples,
  )

  # Team scope: Shared queries
  team_config = CustomizationConfig(
    scope_keys=["team_id"],
    memory_topics=[sql_query_topic],
    generate_memories_examples=examples,
  )

  return [user_config, team_config]


def create_agent_engine(
  project: str,
  location: str,
  model: str = "gemini-2.5-flash",
) -> str:
  """Create an Agent Engine with Memory Bank configuration.

  Args:
    project: Google Cloud project ID.
    location: Google Cloud location (e.g., us-central1).
    model: Model to use for memory generation.

  Returns:
    The Agent Engine ID.
  """
  logger.info("Creating Agent Engine with Memory Bank...")

  client = vertexai.Client(project=project, location=location)

  customization_configs = create_customization_configs()

  agent_engine = client.agent_engines.create(
    config={
      "context_spec": {
        "memory_bank_config": {
          "generation_config": {
            "model": f"projects/{project}/locations/{location}/publishers/google/models/{model}"
          },
          "customization_configs": [
            {
              "scope_keys": config.scope_keys,
              "memory_topics": [
                {"custom_memory_topic": {
                  "label": topic.custom_memory_topic.label,
                  "description": topic.custom_memory_topic.description,
                }}
                for topic in config.memory_topics
              ],
            }
            for config in customization_configs
          ],
        }
      }
    }
  )

  agent_engine_id = agent_engine.api_resource.name.split("/")[-1]
  full_name = agent_engine.api_resource.name

  logger.info("Agent Engine created successfully!")
  logger.info("Agent Engine ID: %s", agent_engine_id)
  logger.info("Full Name: %s", full_name)

  return agent_engine_id


def main():
  """Main entry point for the CLI."""
  parser = argparse.ArgumentParser(
    description="Setup Agent Engine with Memory Bank for BigQuery Data Agent"
  )
  parser.add_argument(
    "--project",
    type=str,
    default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    help="Google Cloud project ID",
  )
  parser.add_argument(
    "--location",
    type=str,
    default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    help="Google Cloud location",
  )
  parser.add_argument(
    "--model",
    type=str,
    default="gemini-2.5-flash",
    help="Model for memory generation",
  )

  args = parser.parse_args()

  if not args.project:
    logger.error("Project ID is required. Use --project or set GOOGLE_CLOUD_PROJECT.")
    sys.exit(1)

  try:
    agent_engine_id = create_agent_engine(
      project=args.project,
      location=args.location,
      model=args.model,
    )

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"\nAdd the following to your .env file:\n")
    print(f"AGENT_ENGINE_ID={agent_engine_id}")
    print("\n" + "=" * 60)

  except Exception as e:
    logger.error("Failed to create Agent Engine: %s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
