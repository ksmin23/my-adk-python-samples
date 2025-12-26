import os
import asyncio
import google.auth
import google.auth.transport.requests
from typing import List
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from .registry import registry

load_dotenv()

# Google Managed MCP Endpoints
MAPS_MCP_URL = "https://mapstools.googleapis.com/mcp"
BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "no_api_found")

# Top-level toolset definitions
maps_toolset = MCPToolset(
  connection_params=StreamableHTTPConnectionParams(
    url=MAPS_MCP_URL,
    headers={"X-Goog-Api-Key": MAPS_API_KEY}
  )
)

def get_bigquery_toolset():
  """Initializes BigQuery toolset with OAuth."""
  try:
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/bigquery"]
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    oauth_token = credentials.token
    
    bigquery_mcp_headers = {
        "Authorization": f"Bearer {oauth_token}",
        "x-goog-user-project": project_id
    }

    return MCPToolset(
      connection_params=StreamableHTTPConnectionParams(
          url=BIGQUERY_MCP_URL,
          headers=bigquery_mcp_headers
      )
    )
  except Exception as e:
    print(f"Failed to initialize BigQuery toolset: {e}")
    return None

def search_available_tools(query: str) -> List[str]:
  """Searches the tool library for useful tools. 
  Use this when you don't have a tool for a specific task. 
  Returns a list of 'ToolName: Description'. 
  Args:
      query: Search keywords (e.g., 'weather', 'places', 'bigquery', 'sql').
  """
  return registry.search(query)

def load_tool(tool_name: str) -> str:
  """Loads a specific tool into your context. 
  Call this after finding a tool with 'search_available_tools'. 
  Args:
      tool_name: The exact name of the tool to load.
  """
  # This function is a signal for the callback.
  tool = registry.get_tool(tool_name)
  if tool:
    return f"Tool '{tool_name}' loaded successfully."
  return f"Error: Tool '{tool_name}' not found."

async def initialize_mcp_tools():
  """Fetches tools from Google Managed MCP servers and registers them."""
  
  # 1. Maps MCP
  if MAPS_API_KEY != "no_api_found":
    try:
      print("--- Initializing Maps MCP Connection ---")
      maps_tools = await maps_toolset.get_tools()
      for tool in maps_tools:
        registry.register(tool)
      print(f"Registered {len(maps_tools)} tools from Maps MCP.")
    except Exception as e:
      print(f"Failed to load Maps MCP: {e}")
  else:
    print("Skipping Maps MCP: GOOGLE_MAPS_API_KEY not found.")

  # 2. BigQuery MCP
  bq_toolset = get_bigquery_toolset()
  if bq_toolset:
    try:
      print("--- Initializing BigQuery MCP Connection ---")
      bq_tools = await bq_toolset.get_tools()
      for tool in bq_tools:
        registry.register(tool)
      print(f"Registered {len(bq_tools)} tools from BigQuery MCP.")
    except Exception as e:
      print(f"Failed to load BigQuery MCP: {e}")

# Auto-initialize MCP tools to populate registry on import
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(initialize_mcp_tools())
    else:
        loop.run_until_complete(initialize_mcp_tools())
except Exception as e:
    # Fallback for environments without a running loop or pre-defined loop
    try:
        asyncio.run(initialize_mcp_tools())
    except Exception as e2:
        print(f"Failed to auto-initialize MCP tools: {e2}")
