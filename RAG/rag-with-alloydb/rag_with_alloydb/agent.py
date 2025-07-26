#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import Toolset
from .prompt import instruction
from . import tools

load_dotenv()

root_agent = LlmAgent(
  model='gemini-2.5-flash',
  name='rag_agent',
  instruction=instruction,
  tools=[
    Toolset.from_tools(
      [tools.search_documents_in_alloydb]
    )
  ],
)