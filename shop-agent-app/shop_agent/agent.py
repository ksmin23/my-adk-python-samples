#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
  MCPToolset,
  StreamableHTTPConnectionParams,
)
from .prompt import instruction

load_dotenv()

# The URL for the remote MCP server. Defaults to http://localhost:9000/mcp/ if not set.
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:9000/mcp/')

# For adk web, MCPToolset should be instantiated directly in the tools list.
# The adk web runner will handle the asynchronous connection lifecycle.
root_agent = LlmAgent(
  model='gemini-2.5-flash',
  name='shop_search_agent',
  instruction=instruction,
  tools=[
    MCPToolset(
      connection_params=StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
      ),
      tool_filter=['search_products']
    )
  ],
)