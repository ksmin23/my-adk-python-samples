#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from toolbox_core import (
    ToolboxSyncClient,
    auth_methods
)

load_dotenv()

TOOLBOX_ENDPOINT = os.getenv("TOOLBOX_ENDPOINT")

def get_google_id_token():
    import google.auth
    from google.auth._credentials_async import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2 import id_token

    # Prefix for Authorization header tokens
    BEARER_TOKEN_PREFIX = auth_methods.BEARER_TOKEN_PREFIX

    if auth_methods._is_cached_token_valid(auth_methods._cached_google_id_token):
        return BEARER_TOKEN_PREFIX + auth_methods._cached_google_id_token["token"]

    credentials, _project_id = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)

    # Create ID token credentials.
    credentials = google.oauth2.id_token.fetch_id_token_credentials(TOOLBOX_ENDPOINT, request=request)

    # Refresh the credential to obtain an ID token.
    credentials.refresh(request)

    new_id_token = getattr(credentials, "token", None)
    expiry = getattr(credentials, "expiry")

    auth_methods._update_token_cache(auth_methods._cached_google_id_token, new_id_token, expiry)

    if new_id_token:
        return BEARER_TOKEN_PREFIX + new_id_token
    else:
        import traceback
        traceback.print_exc()
        raise Exception("Failed to fetch Google ID token.")

auth_token_provider = get_google_id_token

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
