#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import os
from google import genai
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import AgentTool, google_search
from google.genai import types
from dotenv import load_dotenv, find_dotenv

from .prompts import (
    RAG_AGENT_INSTRUCTION,
    SEARCH_AGENT_INSTRUCTION,
    ROOT_AGENT_INSTRUCTION,
)
from .tools import RagAutoIngestor, FileSearchTool, get_store_name

# Load environment variables
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_name = os.getenv("MODEL", "gemini-2.5-flash")
STORE_DISPLAY_NAME = os.getenv("STORE_NAME") 

# Initializing genai client
genai_client = genai.Client()

# Resolve the store name at startup
RESOLVED_STORE_NAME = get_store_name(genai_client, STORE_DISPLAY_NAME)
if not RESOLVED_STORE_NAME:
    logger.warning(f"RagInitialization: Could not resolve store name for '{STORE_DISPLAY_NAME}'.")
else:
    logger.info(f"RagInitialization: Successfully resolved '{STORE_DISPLAY_NAME}' to '{RESOLVED_STORE_NAME}'")

# Specialized RagAgent for retrieval only
rag_agent = Agent(
    model=model_name,
    name="RagAgent",
    description="Agent specialized in searching the internal knowledge base",
    instruction=RAG_AGENT_INSTRUCTION,
    tools=[FileSearchTool(store_name=RESOLVED_STORE_NAME)],
)

search_agent = Agent(
    model=model_name,
    name="SearchAgent",
    description="Agent to perform Google Search",
    instruction=SEARCH_AGENT_INSTRUCTION,
    tools=[google_search],
)

root_agent = Agent(
    name="basic_agent_adk",
    description="Helpful AI assistant with automatic RAG ingestion.",
    model=Gemini(
        model=model_name,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        RagAutoIngestor(genai_client=genai_client, store_name=RESOLVED_STORE_NAME),
        AgentTool(agent=rag_agent),
        AgentTool(agent=search_agent),
    ],
)
