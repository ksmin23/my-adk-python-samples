from google.adk.agents import Agent
from toolbox_core import ToolboxSyncClient, auth_methods

TOOLBOX_ENDPOINT = 'https://toolbox-vsi6xb4zha-uc.a.run.app'
auth_token_provider = auth_methods.get_google_id_token

# MUST RUN!!! before get adk agent started
# gcloud auth application-default login

# Replace with the Cloud Run service URL generated in the previous step.
toolbox = ToolboxSyncClient(
    TOOLBOX_ENDPOINT,
    client_headers={"Authorization": auth_token_provider},                          
)

# Load all the tools
tools = toolbox.load_toolset('my_bq_toolset')

root_agent = Agent(
    model='gemini-2.0-flash-001',
    name='root_agent',
    description=(
        "Agent to answer questions about Google Cloud Release notes."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the Google Cloud Release notes. Use the tools to answer the question"
    ),
    tools=tools,
)

