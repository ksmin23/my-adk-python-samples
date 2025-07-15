import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from toolbox_core import (
    ToolboxSyncClient,
    auth_methods
)

load_dotenv()

TOOLBOX_ENDPOINT = os.getenv("TOOLBOX_ENDPOINT")

# def get_google_id_token(): # not working
#     import google.auth
#     from google.auth._credentials_async import Credentials
#     from google.auth.transport.requests import AuthorizedSession, Request

#     # Prefix for Authorization header tokens
#     BEARER_TOKEN_PREFIX = "Bearer "

#     credentials, _project_id = google.auth.default()
#     print(f"[ksmin] Project ID={_project_id}")
#     print("[ksmin] cred_info(1): ", credentials.get_cred_info())
#     print("[ksmin] id_token(1): ", getattr(credentials, "id_token", None))
#     session = AuthorizedSession(credentials)
#     request = Request(session)
#     credentials.refresh(request)
#     print("[ksmin] cred_info(2): ", credentials.get_cred_info())
#     print("[ksmin] id_token(2): ", getattr(credentials, "id_token", None))
#     new_id_token = getattr(credentials, "id_token", None)
#     expiry = getattr(credentials, "expiry")

#     if new_id_token:
#         print(f'[ksmin] new_id_token: {new_id_token[:10]} ...')
#         print(f'[ksmin] expiry: {expiry}')
#         return BEARER_TOKEN_PREFIX + new_id_token
#     else:
#         import traceback
#         traceback.print_exc()
#         raise Exception("Failed to fetch Google ID token.")


# def get_google_id_token(): # working
#     import google.auth
#     from google.auth._credentials_async import Credentials
#     from google.auth.transport.requests import AuthorizedSession, Request
#     from google.oauth2 import id_token

#     # Prefix for Authorization header tokens
#     BEARER_TOKEN_PREFIX = "Bearer "

#     credentials, _project_id = google.auth.default()
#     print(f"[ksmin] Project ID={_project_id}")
#     print("[ksmin] cred_info(1): ", credentials.get_cred_info())
#     print("[ksmin] id_token(1): ", getattr(credentials, "id_token", None))
#     session = AuthorizedSession(credentials)
#     request = Request(session)

#     # ID 토큰을 얻기 위한 명시적인 요청
#     id_token_audience = TOOLBOX_ENDPOINT
#     # id_token_value = id_token.fetch_id_token(Request(), id_token_audience)
#     new_id_token = id_token.fetch_id_token(request, id_token_audience)

#     expiry = getattr(credentials, "expiry")

#     if new_id_token:
#         print(f'[ksmin] new_id_token: {new_id_token[:10]} ...')
#         print(f'[ksmin] expiry: {expiry}')
#         return BEARER_TOKEN_PREFIX + new_id_token
#     else:
#         import traceback
#         traceback.print_exc()
#         raise Exception("Failed to fetch Google ID token.")

def get_google_id_token():
    import google.auth
    from google.auth._credentials_async import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2 import id_token

    # Prefix for Authorization header tokens
    BEARER_TOKEN_PREFIX = auth_methods.BEARER_TOKEN_PREFIX # "Bearer "

    credentials, _project_id = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)

    # Create ID token credentials.
    credentials = google.oauth2.id_token.fetch_id_token_credentials(TOOLBOX_ENDPOINT, request=request)

    # Refresh the credential to obtain an ID token.
    credentials.refresh(request)

    new_id_token = getattr(credentials, "token", None)
    expiry = getattr(credentials, "expiry")

    if new_id_token:
        return BEARER_TOKEN_PREFIX + new_id_token
    else:
        import traceback
        traceback.print_exc()
        raise Exception("Failed to fetch Google ID token.")

auth_methods.get_google_id_token = get_google_id_token 
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
    model='gemini-2.5-flash',
    name='root_agent',
    description=(
        "Agent to answer questions about Google Cloud Release notes."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the Google Cloud Release notes."
        " Use the tools to answer the question"
    ),
    tools=tools,
)
