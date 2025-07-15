#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    # StdioServerParameters,
    StreamableHTTPConnectionParams,
)

load_dotenv()

# # The absolute path to the directory where the agent.py file is located.
# AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# # The absolute path to the mcp-search-server directory, which contains the server.py script and the .env file.
# # This path is constructed relative to the location of this agent file.
# MCP_SERVER_DIR = os.path.abspath(os.path.join(AGENT_DIR, '..', '..', 'mcp-search-server'))

# # The absolute path to the server.py script.
# MCP_SERVER_SCRIPT = os.path.join(MCP_SERVER_DIR, 'server.py')

# The URL for the remote MCP server. Defaults to http://localhost:8000/mcp if not set.
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:9000/mcp')

# instruction = f'''
#     You are a shopping assistant. Use the available tools to search for products based on the user\'s query. '
#     You should use the `search_products` tool to find products in the catalog.
# '''

# instruction = f'''
#     Your role is a shop search agent on an e-commerce site with millions of
#     items. Your responsibility is to search items based on the queries you
#     recieve.

#     To find items use `search_products` tool by passing a list of queries,
#     and answer to the user with item's name, description and img_url
# '''

instruction = f'''
    Your role is a shop search agent on an e-commerce site with millions of
    items. Your responsibility is to search items based on the queries you
    recieve.

    To find items use `search_products` tool by passing a list of queries,
    and answer to the user
'''

# For adk web, MCPToolset should be instantiated directly in the tools list.
# The adk web runner will handle the asynchronous connection lifecycle.
root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='shop_search_agent',
    instruction=instruction,
    tools=[
        # MCPToolset(
        #     connection_params=StdioServerParameters(
        #         command='python3',
        #         args=[MCP_SERVER_SCRIPT],
        #         # The working directory is set to the server\'s directory to ensure
        #         # it can find the .env file.
        #         cwd=MCP_SERVER_DIR,
        #     ),
        #     # The tool_filter is not strictly necessary if the server only has one tool,
        #     # but it\'s good practice to be explicit.
        #     tool_filter=['search_products']
        # )
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_SERVER_URL
            ),
            tool_filter=['search_products']
        )
    ],
)
