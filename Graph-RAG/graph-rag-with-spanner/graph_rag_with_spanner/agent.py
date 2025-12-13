#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from .prompt import instruction
from . import tools

load_dotenv()

root_agent = Agent(
  model='gemini-2.5-flash',
  name='spanner_graph_rag_agent',
  instruction=instruction,
  tools=[tools.retrieve_graph_context],
)
