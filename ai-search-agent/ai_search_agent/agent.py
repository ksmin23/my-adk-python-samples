#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import google_search
from .prompts import instruction_ai_search

load_dotenv()

root_agent = Agent(
  model="gemini-1.5-flash",
  name="ai_search_agent",
  description=(
    "An AI-powered search agent that uses advanced Google Search operators "
    "to find high-quality, filtered information."
  ),
  instruction=instruction_ai_search,
  tools=[google_search],
)
