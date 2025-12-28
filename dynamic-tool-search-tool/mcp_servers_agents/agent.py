#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# This implementation is based on the source code and patterns described in the following article:
# https://medium.com/google-cloud/implementing-anthropic-style-dynamic-tool-search-tool-f39d02a35139

import logging
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from .lib.registry import registry
from .lib.tools import search_available_tools, load_tool, initialize_mcp_tools

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def dynamic_loader_callback(
  tool,
  args,
  tool_context,
  tool_response
):
  """Callback to intercept 'load_tool' and inject the requested tool."""
  # Use global root_agent to access tools list
  global root_agent
  
  # Get tool name as a string
  tool_name_str = getattr(tool, 'name', str(tool))
  
  if "load_tool" in tool_name_str:
    requested_name = args.get('tool_name')
    new_tool = registry.get_tool(requested_name)
    
    if new_tool:
      # Access the agent tools list
      current_names = [getattr(t, 'name', getattr(t, '__name__', '')) for t in root_agent.tools]

      if requested_name not in current_names:
        root_agent.tools.append(new_tool)
        logger.info(f"[System] Dynamically injected tool: {requested_name}")
        return tool_response
    else:
      logger.warning(f"[System] Requested tool not found in registry: {requested_name}")

  return tool_response

# Initialize the Agent with minimal tools
root_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="mcp_dynamic_agent",
  instruction="""
  You are an advanced assistant with access to a vast library of tools from Google Managed MCP servers.
  
  To use tools efficiently:
  1. Use 'search_available_tools' to find relevant tools when you don't have a direct tool for the user's request.
  2. Once you identify a promising tool name, use 'load_tool' to bring it into your current context.
  3. After the tool is loaded, you can then call that tool in the next turn to fulfill the request.
  
  Always mention to the user that you are searching for and loading the necessary tools.
  """,
  tools=[search_available_tools, load_tool],
  after_tool_callback=dynamic_loader_callback
)
