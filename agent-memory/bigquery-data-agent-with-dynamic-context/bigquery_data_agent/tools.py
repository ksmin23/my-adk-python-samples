#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Tools for BigQuery Data Agent with Agent Engine Memory Bank."""

import logging
import os
import re
import traceback
from datetime import datetime
from typing import Any, Literal, Optional

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


def _extract_dataset_id(sql: str) -> str:
  """Extracts the dataset_id from a BigQuery SQL query.

  Looks for project.dataset.table or dataset.table patterns.

  Args:
    sql: The SQL query string.

  Returns:
    The extracted dataset_id or 'unknown'.
  """
  # Matches: `project.dataset.table`, project.dataset.table, dataset.table
  # Pattern 1: project.dataset.table (3 parts)
  match = re.search(r"([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)\.[a-zA-Z0-9_-]+", sql)
  if match:
    return match.group(2)
  
  # Pattern 2: dataset.table (2 parts)
  match = re.search(r"([a-zA-Z0-9_-]+)\.[a-zA-Z0-9_-]+", sql)
  if match:
    return match.group(1)
  
  return "unknown"


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
      sql = args.get("sql", "")
      tool_context.state["last_executed_query"] = sql
      tool_context.state["last_query_results"] = tool_response.get("rows", [])
      tool_context.state["last_dataset_id"] = _extract_dataset_id(sql)

  return None


def _parse_memory_fact(fact: str) -> dict[str, Any]:
  """Parses a structured memory fact string into a dictionary.

  The fact string is expected to have fields like 'Title:', 'Description:',
  'NL Query:', and 'SQL:'. Multi-line values are supported.

  Args:
    fact: The raw fact string from memory.

  Returns:
    A dictionary containing the parsed fields.
  """

  parsed = {"fact": fact}

  # Mapping of prefixes to match_entry keys
  key_map = {
    "title:": "title",
    "description:": "description",
    "nl query:": "nl_query",
    "sql:": "sql_query",
  }

  current_key = None
  for line in fact.split("\n"):
    line_lower = line.lower()
    # Check if line starts with any of our known prefixes
    matched = False
    for prefix, entry_key in key_map.items():
      if line_lower.startswith(prefix):
        current_key = entry_key
        parsed[current_key] = line.split(":", 1)[1].strip()
        matched = True
        break

    if not matched and current_key:
      # Append multi-line content for the last found key
      parsed[current_key] += "\n" + line

  return parsed


async def _save_user_property(
  key: str,
  value: str,
  tool_context: ToolContext,
) -> None:
  """Internal helper to save a user property to personal memory."""
  memory_service = tool_context._invocation_context.memory_service
  if not memory_service:
    return

  client = memory_service._get_api_client()
  agent_engine_id = memory_service._agent_engine_id
  agent_engine_name = f"reasoningEngines/{agent_engine_id}"
  user_id = tool_context._invocation_context.user_id
  app_name = tool_context._invocation_context.session.app_name

  user_scope = {"app_name": app_name, "user_id": user_id}
  fact = f"User property {key}: {value}"

  client.agent_engines.memories.generate(
    name=agent_engine_name,
    scope=user_scope,
    direct_memories_source={"direct_memories": [{"fact": fact}]},
    config={
      "wait_for_completion": False,
      "metadata": {
        "content_type": {"string_value": "profile"},
        "property_key": {"string_value": key},
      },
    },
  )
  logger.info("Auto-registered user property '%s' = '%s'", key, value)
  # Update state for immediate session use
  tool_context.state[key] = value


async def set_user_property(
  key: str,
  value: str,
  tool_context: ToolContext,
) -> dict:
  """Sets a persistent property for the user in their personal memory scope.

  This is useful for storing information like 'team_id' that should persist
  across sessions.

  Args:
    key: The property name (e.g., 'team_id').
    value: The property value.
    tool_context: The ADK tool context.

  Returns:
    A status message indicating success or failure.
  """
  try:
    await _save_user_property(key, value, tool_context)
    return {
      "status": "success",
      "message": f"Successfully saved {key} as '{value}'. This will be remembered across sessions.",
    }
  except Exception as e:
    logger.error("Failed to save user property: %s", e)
    return {"status": "error", "message": str(e)}


async def get_team_id_from_user_memory(tool_context: ToolContext) -> str | None:
  """Attempts to retrieve team_id from the user's personal memory scope.

  Searches for memories in the 'user' scope that mention 'team id'.

  Args:
    tool_context: The ADK tool context.

  Returns:
    The extracted team_id string or None if not found.
  """
  try:
    memory_service = tool_context._invocation_context.memory_service
    if not memory_service:
      return None

    client = memory_service._get_api_client()
    agent_engine_id = memory_service._agent_engine_id
    agent_engine_name = f"reasoningEngines/{agent_engine_id}"
    user_id = tool_context._invocation_context.user_id
    app_name = tool_context._invocation_context.session.app_name

    user_scope = {"app_name": app_name, "user_id": user_id}

    # Step 1: Try structured retrieval using metadata filter
    try:
      filter_groups = [
        {
          "filters": [
            {"key": "content_type", "value": {"string_value": "profile"}, "op": "EQUAL"},
            {"key": "property_key", "value": {"string_value": "team_id"}, "op": "EQUAL"}
          ]
        }
      ]
      
      response = client.agent_engines.memories.retrieve(
        name=agent_engine_name,
        scope=user_scope,
        config={"filter_groups": filter_groups},
      )
      
      for memory in list(response):
        fact = memory.memory.fact if hasattr(memory, "memory") else str(memory)
        # Match "User property team_id: value"
        match = re.search(r"property team_id:\s*([a-zA-Z0-9_-]+)", fact, re.IGNORECASE)
        if match:
          val = match.group(1)
          logger.info("Found team_id '%s' via metadata filter", val)
          return val
    except Exception as me:
      logger.debug("Metadata-based profile lookup failed: %s", me)

    # Step 2: Fallback to semantic search with robust regex
    # Search for "my team id" or "team name" in personal memory
    response = client.agent_engines.memories.retrieve(
      name=agent_engine_name,
      scope=user_scope,
      # top_k: Max memories to return (Default: 3, Max: 100)
      similarity_search_params={
        "search_query": "What is my team id or team name?",
        "top_k": 5
      }
    )

    for memory in list(response):
      fact = memory.memory.fact if hasattr(memory, "memory") else str(memory)
      # Improved regex to handle "team ID is X", "team: X", "I'm in team X", "data-ops 팀 소속", etc.
      # Korean support included via context words
      match = re.search(r"(?:team(?:\s|_|)id|team|팀)\s*(?:is|:|\s|이|소속|ID)\s*([a-zA-Z0-9_-]+)", fact, re.IGNORECASE)
      if match:
        team_id = match.group(1)
        logger.info("Found team_id '%s' in user memory via regex", team_id)
        return team_id

  except Exception as e:
    logger.warning("Failed to lookup team_id in memory: %s", e)
  
  return None


async def save_query_to_memory(
  title: str,
  description: str,
  nl_query: str,
  sql_query: str,
  scope: Literal["user", "team"],
  tool_context: ToolContext,
  team_id: Optional[str] = None,
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
    team_id: Optional team ID strings (e.g., "sales-team"). If provided, it overrides the default or state-cached team ID.

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

  # Resolving context will happen inside the try block using the service
  try:
    memory_service = tool_context._invocation_context.memory_service
    if not memory_service:
      return {
        "status": "error",
        "message": "Memory service not available in context.",
      }

    client = memory_service._get_api_client()
    agent_engine_id = memory_service._agent_engine_id
    agent_engine_name = f"reasoningEngines/{agent_engine_id}"
    user_id = tool_context._invocation_context.user_id
    app_name = tool_context._invocation_context.session.app_name
    
    # Determine scope dict based on scope parameter
    if scope == "user":
      memory_scope = {"app_name": app_name, "user_id": user_id}
    else:  # team
      # Resolve team_id only when needed for team scope: parameter > state > user memory profile
      if not team_id:
        team_id = tool_context.state.get("team_id")

      if not team_id:
        team_id = await get_team_id_from_user_memory(tool_context)
        if team_id:
          tool_context.state["team_id"] = team_id

      if not team_id:
        return {
          "status": "error",
          "message": "Team ID is required for team scope. Please provide it or save it in your profile first.",
        }
      
      # Auto-register team_id to user profile for future sessions
      try:
        await _save_user_property("team_id", team_id, tool_context)
      except Exception as pe:
        logger.debug("Minor failure during team_id auto-registration: %s", pe)

      memory_scope = {"app_name": app_name, "team_id": team_id}

    # Create structured memory fact with title, description, and query
    fact = f"""Title: {title}
Description: {description}
NL Query: {nl_query}
SQL: {sql_query}"""

    # Try to get dataset_id from state (stored during execution)
    # Fallback to extracting from current query, then to environment variable
    dataset_id = tool_context.state.get("last_dataset_id")
    if not dataset_id or dataset_id == "unknown":
      dataset_id = _extract_dataset_id(sql_query)

    if dataset_id == "unknown":
      dataset_id = os.environ.get("BIGQUERY_DATASET", "unknown")

    # Store directly to the appropriate scope using Agent Engine SDK
    client.agent_engines.memories.generate(
      name=agent_engine_name,
      scope=memory_scope,
      direct_memories_source={
        "direct_memories": [
          {
            "fact": fact,
          }
        ]
      },
      config={
        "wait_for_completion": False,
        "metadata": {
          "dataset_id": {"string_value": dataset_id},
          "content_type": {"string_value": "sql"},
        },
      },
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
    traceback.print_exc()
    logger.error("Failed to save query to memory: %s", e)
    return {
      "status": "error",
      "message": f"Failed to save query: {str(e)}",
    }


async def search_query_history(
  nl_query: str,
  scope: Literal["user", "team", "global"],
  tool_context: ToolContext,
  team_id: Optional[str] = None,
) -> dict[str, Any]:
  """Search the Memory Bank for similar past queries with scope-based retrieval.

  Uses Agent Engine SDK directly to search memories in the appropriate scope(s).
  Parses stored query format with title, description, NL query, and SQL.

  Args:
    nl_query: The natural language query to search for.
    scope: The search scope - 'user', 'team', or 'global'.
    tool_context: The ADK tool context.
    team_id: Optional team ID strings. If provided, it overrides the default or state-cached team ID for team-scoped search.

  Returns:
    A dictionary containing matching queries or an empty list.
  """
  logger.info("Searching query history with scope: %s", scope)

  # Resolving context will happen inside the try block using the service
  try:
    memory_service = tool_context._invocation_context.memory_service
    if not memory_service:
      logger.warning("Memory service not available, returning empty results")
      return {
        "status": "success",
        "message": "Memory service not available. Proceeding without history.",
        "matches": [],
      }

    client = memory_service._get_api_client()
    agent_engine_id = memory_service._agent_engine_id
    agent_engine_name = f"reasoningEngines/{agent_engine_id}"
    user_id = tool_context._invocation_context.user_id
    app_name = tool_context._invocation_context.session.app_name
    
    # Resolve team_id only for team or global scope: parameter > state > user memory profile
    if scope in ["team", "global"]:
      if not team_id:
        team_id = tool_context.state.get("team_id")
      
      if not team_id:
        team_id = await get_team_id_from_user_memory(tool_context)
        if team_id:
          tool_context.state["team_id"] = team_id

    matches = []

    # Define scopes to search based on the requested scope
    scopes_to_search = []
    if scope == "user":
      scopes_to_search = [{"app_name": app_name, "user_id": user_id} ]
    elif scope == "team":
      scopes_to_search = [{"app_name": app_name, "team_id": team_id}]
    else:  # global - search both user and team
      scopes_to_search = [
        {"app_name": app_name, "user_id": user_id},
        {"app_name": app_name, "team_id": team_id}
      ]

    # Search each scope with similarity search
    for memory_scope in scopes_to_search:
      scope_name = "user" if "user_id" in memory_scope else "team"

      # Filter for SQL-type memories only
      filter_groups = [
        {
          "filters": [
            {
              "key": "content_type",
              "value": {"string_value": "sql"},
              "op": "EQUAL",
            }
          ]
        }
      ]

      response = client.agent_engines.memories.retrieve(
        name=agent_engine_name,
        scope=memory_scope,
        similarity_search_params={"search_query": nl_query},
        config={"filter_groups": filter_groups},
      )

      for memory in list(response):
        fact = memory.memory.fact if hasattr(memory, "memory") else str(memory)
        match_entry = _parse_memory_fact(fact)
        match_entry["scope"] = scope_name
        matches.append(match_entry)

    return {
      "status": "success",
      "match_count": len(matches),
      "matches": matches[:5],  # Return top 5 matches
    }

  except Exception as e:
    traceback.print_exc()
    logger.error("Failed to search query history: %s", e)
    return {
      "status": "error",
      "message": f"Search failed: {str(e)}",
      "matches": [],
    }
