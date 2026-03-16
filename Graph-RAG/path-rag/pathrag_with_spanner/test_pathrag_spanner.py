#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

try:
  from .agent import root_agent as agent
except ImportError:
  from agent import root_agent as agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent():
  # 1. Test standard query
  query = "What is PathRAG and how does it work?"
  logger.info(f"Testing query: {query}")
  
  # ADK agent query method (if implemented, or direct tool call via agent?)
  # agent.query() might be what we want if we used the standard ADK Agent class runner pattern?
  # ADK Agent class usually has a query/invoke method? 
  # Let's check `google.adk.agents.llm_agent.Agent`.
  # Based on usage in other samples, `agent.query()` or `agent.generate_response()` might be used.
  
  try:
    response = await agent.query(query)
    print("\n=== Agent Response ===")
    print(response)
    print("======================\n")
  except AttributeError:
    # Fallback if query method is named differently or we need to run via runner
    logger.warning("Agent.query() method not found. Attempting manual tool invocation if possible, or check ADK version.")
    pass

if __name__ == "__main__":
  if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
    logger.error("GOOGLE_CLOUD_PROJECT not set.")
  else:
    asyncio.run(test_agent())
