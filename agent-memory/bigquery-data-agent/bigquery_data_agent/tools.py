"""Tools for BigQuery Data Agent with Agent Engine Memory Bank."""

import logging
import os
from datetime import datetime
from typing import Any, Literal

from dotenv import load_dotenv
from google.adk.tools import BaseTool, ToolContext
from google.adk.tools.bigquery import BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

# Load .env file (auto-discovers from current directory or parents)
load_dotenv()

logger = logging.getLogger(__name__)


# BigQuery Toolset configuration
# WriteMode.BLOCKED prevents destructive operations (INSERT, UPDATE, DELETE, DROP)
bigquery_tool_config = BigQueryToolConfig(
  write_mode=WriteMode.BLOCKED,
)

# Create BigQueryToolset with all available tools
bigquery_toolset = BigQueryToolset(
  bigquery_tool_config=bigquery_tool_config,
)


# Module-level cache for vertexai client
_vertexai_client = None


def _get_vertexai_client():
  """Get or create a cached vertexai client."""
  global _vertexai_client
  if _vertexai_client is None:
    import vertexai
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    _vertexai_client = vertexai.Client(project=project, location=location)
  return _vertexai_client


def _get_agent_engine_name() -> str:
  """Get the full Agent Engine resource name."""
  project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
  location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
  agent_engine_id = os.environ.get("AGENT_ENGINE_ID", "")
  return f"projects/{project}/locations/{location}/reasoningEngines/{agent_engine_id}"


def store_query_result_in_state(
  tool: BaseTool,
  args: dict[str, Any],
  tool_context: ToolContext,
  tool_response: dict,
) -> dict | None:
  """After-tool callback to store BigQuery results in state for potential saving.

  Args:
    tool: The tool that was executed.
    args: The arguments passed to the tool.
    tool_context: The ADK tool context.
    tool_response: The response from the tool.

  Returns:
    None (does not modify the response).
  """
  if tool.name == "execute_sql":
    if tool_response.get("status") == "SUCCESS":
      tool_context.state["last_executed_query"] = args.get("sql", "")
      tool_context.state["last_query_results"] = tool_response.get("rows", [])
  return None


async def save_query_to_memory(
  title: str,
  description: str,
  nl_query: str,
  sql_query: str,
  scope: Literal["user", "team"],
  tool_context: ToolContext,
) -> dict[str, Any]:
  """Save a validated query to the Memory Bank with scope-based storage.

  Uses Agent Engine SDK directly to store memories in the appropriate scope.
  Stores title, description, NL query, and SQL for accurate search.

  Args:
    title: A concise name for the query (e.g., "월별 매출 합계").
    description: What the query does and when to use it.
    nl_query: The natural language question that the query answers.
    sql_query: The SQL query that was validated as correct.
    scope: The sharing scope - 'user' for personal, 'team' for shared.
    tool_context: The ADK tool context.

  Returns:
    A status message indicating success or failure.
  """
  logger.info("Saving query to memory with scope: %s", scope)

  # Safety check: only save SELECT queries
  sql_stripped = sql_query.strip().lower()
  if not sql_stripped.startswith("select"):
    return {
      "status": "error",
      "message": "Only SELECT queries can be saved.",
    }

  # Get context from session state
  user_id = tool_context.state.get("user_id", "anonymous")
  team_id = tool_context.state.get("team_id", "default")

  # Check AGENT_ENGINE_ID is configured
  if not os.environ.get("AGENT_ENGINE_ID"):
    return {
      "status": "error",
      "message": "AGENT_ENGINE_ID not configured. Run setup_memory_bank.py first.",
    }

  try:
    client = _get_vertexai_client()
    agent_engine_name = _get_agent_engine_name()

    # Determine scope dict based on scope parameter
    if scope == "user":
      memory_scope = {"user_id": user_id}
    else:  # team
      memory_scope = {"team_id": team_id}

    # Create structured memory fact with title, description, and query
    fact = f"""Title: {title}
Description: {description}
NL Query: {nl_query}
SQL: {sql_query}"""

    # Store directly to the appropriate scope using Agent Engine SDK
    client.agent_engines.memories.generate(
      name=agent_engine_name,
      scope=memory_scope,
      direct_memories_source={"direct_memories": [{"fact": fact}]},
      config={"wait_for_completion": True},
    )

    logger.info("Memory saved to %s scope: %s", scope, title)

    return {
      "status": "success",
      "message": f"Query '{title}' saved to {scope} memory.",
      "title": title,
      "scope": scope,
      "query_id": f"{user_id}_{datetime.now().timestamp()}",
    }

  except Exception as e:
    logger.error("Failed to save query to memory: %s", e)
    return {
      "status": "error",
      "message": f"Failed to save query: {str(e)}",
    }


async def search_query_history(
  nl_query: str,
  scope: Literal["user", "team", "global"],
  tool_context: ToolContext,
) -> dict[str, Any]:
  """Search the Memory Bank for similar past queries with scope-based retrieval.

  Uses Agent Engine SDK directly to search memories in the appropriate scope(s).
  Parses stored query format with title, description, NL query, and SQL.

  Args:
    nl_query: The natural language query to search for.
    scope: The search scope - 'user', 'team', or 'global'.
    tool_context: The ADK tool context.

  Returns:
    A dictionary containing matching queries or an empty list.
  """
  logger.info("Searching query history with scope: %s", scope)

  user_id = tool_context.state.get("user_id", "anonymous")
  team_id = tool_context.state.get("team_id", "default")

  # Check AGENT_ENGINE_ID is configured
  if not os.environ.get("AGENT_ENGINE_ID"):
    logger.warning("AGENT_ENGINE_ID not configured, returning empty results")
    return {
      "status": "success",
      "message": "AGENT_ENGINE_ID not configured. Proceeding without history.",
      "matches": [],
    }

  try:
    client = _get_vertexai_client()
    agent_engine_name = _get_agent_engine_name()

    matches = []

    # Define scopes to search based on the requested scope
    scopes_to_search = []
    if scope == "user":
      scopes_to_search = [{"user_id": user_id}]
    elif scope == "team":
      scopes_to_search = [{"team_id": team_id}]
    else:  # global - search both user and team
      scopes_to_search = [{"user_id": user_id}, {"team_id": team_id}]

    # Search each scope with similarity search
    for memory_scope in scopes_to_search:
      scope_name = "user" if "user_id" in memory_scope else "team"

      response = client.agent_engines.memories.retrieve(
        name=agent_engine_name,
        scope=memory_scope,
        similarity_search_params={"search_query": nl_query},
      )

      for memory in list(response):
        fact = memory.memory.fact if hasattr(memory, "memory") else str(memory)

        # Parse the stored fact format
        match_entry = {"fact": fact, "scope": scope_name}

        lines = fact.split("\n")
        for line in lines:
          line_lower = line.lower()
          if line_lower.startswith("title:"):
            match_entry["title"] = line.split(":", 1)[1].strip()
          elif line_lower.startswith("description:"):
            match_entry["description"] = line.split(":", 1)[1].strip()
          elif line_lower.startswith("nl query:"):
            match_entry["nl_query"] = line.split(":", 1)[1].strip()
          elif line_lower.startswith("sql:"):
            match_entry["sql_query"] = line.split(":", 1)[1].strip()

        matches.append(match_entry)

    return {
      "status": "success",
      "match_count": len(matches),
      "matches": matches[:5],  # Return top 5 matches
    }

  except Exception as e:
    logger.error("Failed to search query history: %s", e)
    return {
      "status": "error",
      "message": f"Search failed: {str(e)}",
      "matches": [],
    }
