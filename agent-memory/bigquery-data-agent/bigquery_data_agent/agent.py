"""BigQuery Data Agent with Agent Engine Memory Bank integration."""

import logging
import os
from datetime import date

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.adk.tools.load_memory_tool import load_memory_tool
from google.genai import types

# Load .env file (auto-discovers from current directory or parents)
load_dotenv()


from .prompts import get_system_instruction
from .tools import (
  bigquery_toolset,
  save_query_to_memory,
  search_query_history,
  store_query_result_in_state,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def get_schema_info() -> str:
  """Retrieve schema information for the configured BigQuery dataset.

  Returns:
    A string containing schema information for the agent's context.
  """
  # TODO: Implement dynamic schema retrieval from BigQuery
  # For now, return a placeholder that should be configured
  schema_placeholder = f"""
<SCHEMA>
Project: {os.environ.get("GOOGLE_CLOUD_PROJECT", "")}
Dataset: {os.environ.get("BIGQUERY_DATASET", "")}

(Schema information will be loaded dynamically.
Configure BIGQUERY_DATASET in .env or implement schema retrieval.)
</SCHEMA>
"""
  return schema_placeholder


async def auto_save_session_to_memory_callback(
  callback_context: CallbackContext,
) -> None:
  """Callback to automatically save session to memory after each interaction.

  This enables the Agent Engine to maintain conversational context.
  """
  try:
    memory_service = callback_context._invocation_context.memory_service
    if memory_service:
      await memory_service.add_session_to_memory(
        callback_context._invocation_context.session
      )
  except Exception as e:
    logger.warning("Failed to save session to memory: %s", e)


def get_root_agent() -> LlmAgent:
  """Create and configure the BigQuery Data Agent."""

  # Combine instructions
  # Prepend the general agent identity and runtime context
  full_instruction = f"""
You are a BigQuery Data Agent with access to the Memory Bank.
Today's date: {date.today()}
Project: {os.environ.get("GOOGLE_CLOUD_PROJECT", "")}
Dataset: {os.environ.get("BIGQUERY_DATASET", "")}

{get_system_instruction()}

{get_schema_info()}
"""

  agent = LlmAgent(
    model=os.environ.get("AGENT_MODEL", "gemini-2.5-flash"),
    name="bigquery_data_agent",
    description="A self-learning BigQuery agent that converts natural language to SQL and learns from past queries.",
    instruction=full_instruction,
    tools=[
      bigquery_toolset,  # ADK BigQueryToolset with execute_sql
      save_query_to_memory,
      search_query_history,
      preload_memory_tool,  # ADK built-in tool for memory preloading
      load_memory_tool,     # ADK built-in tool for selective memory loading
    ],
    after_tool_callback=store_query_result_in_state,
    after_agent_callback=auto_save_session_to_memory_callback,
    generate_content_config=types.GenerateContentConfig(
      temperature=0.01,  # Low temperature for consistent SQL generation
    ),
  )

  return agent


# Create the root agent instance
root_agent = get_root_agent()
