#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from google.adk.agents import Agent
from google.adk.tools import google_search

from ..prompts import instruction_research

research_agent = Agent(
  model="gemini-2.5-flash",
  name="research_agent",
  description=(
    "A market researcher for an e-commerce site. Receives a search request "
    "from a user, and returns a list of 5 generated queries in English."
  ),
  instruction=instruction_research,
  tools=[google_search],
)