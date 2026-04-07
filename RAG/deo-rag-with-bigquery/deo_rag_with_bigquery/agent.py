#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv, find_dotenv
from google.adk.agents import LlmAgent
from .prompt import instruction
from . import tools

load_dotenv(find_dotenv())

root_agent = LlmAgent(
  model='gemini-2.5-flash',
  name='deo_rag_agent',
  instruction=instruction,
  tools=[tools.search_documents, tools.deo_search_documents],
)
