#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from .prompt import PATHRAG_AGENT_INSTRUCTION
from . import tools

load_dotenv()

root_agent = Agent(
  model="gemini-2.5-flash",
  name="pathrag_agent",
  instruction=PATHRAG_AGENT_INSTRUCTION,
  tools=[tools.pathrag_tool],
)
