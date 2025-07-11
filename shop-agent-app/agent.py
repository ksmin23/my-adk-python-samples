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

async def create_agent():
    """Creates an agent by connecting to the Vertex AI Search MCP server."""
    print("Attempting to connect to Vertex AI Search for Retail MCP server...")
    
    # Asynchronously create the toolset from the MCP server.
    # MCPToolset.from_server returns the toolset and an exit_stack for cleanup.
    shop_search_tools, exit_stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command='python3',
            args=[MCP_SERVER_SCRIPT],
            # The working directory is set to the server's directory to ensure
            # it can find the .env file.
            cwd=MCP_SERVER_DIR,
        ),
        # The tool_filter is not strictly necessary if the server only has one tool,
        # but it's good practice to be explicit.
        tool_filter=['search_products']
    )
    
    print("Vertex AI Search for Retail MCP Toolset created successfully.")

    # Create the LlmAgent with the tools obtained from the MCP server.
    agent = LlmAgent(
        model='gemini-2.5-flash',
        name='shop_search_agent',
        instruction='You are a shopping assistant. Use the available tools to search for products based on the user\'s query. '
                    'You should use the `search_products` tool to find products in the catalog.',
        tools=shop_search_tools,
    )

    # Return the agent and the exit_stack to be managed by the runner.
    return agent, [exit_stack]

# The root_agent is now an awaitable that will be resolved by the ADK runner.
root_agent = create_agent()
