import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# The absolute path to the directory where the agent.py file is located.
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# The absolute path to the mcp-search-server directory, which contains the server.py script and the .env file.
# This path is constructed relative to the location of this agent file.
MCP_SERVER_DIR = os.path.abspath(os.path.join(AGENT_DIR, '..', '..', 'mcp-search-server'))

# The absolute path to the server.py script.
MCP_SERVER_SCRIPT = os.path.join(MCP_SERVER_DIR, 'server.py')

root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='shop_search_agent',
    instruction='You are a shopping assistant. Use the available tools to search for products based on the user\'s query. '
                'You should use the `search_products` tool to find products in the catalog.',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='python3',
                args=[MCP_SERVER_SCRIPT],
                # The working directory is set to the server\'s directory to ensure
                # it can find the .env file.
                cwd=MCP_SERVER_DIR,
            ),
            # The tool_filter is not strictly necessary if the server only has one tool,
            # but it\'s good practice to be explicit.
            tool_filter=['search_products']
        )
    ],
)
