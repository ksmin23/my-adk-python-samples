#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import asyncio
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

try:
  from .agent import root_agent
except ImportError:
  from agent import root_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_ID = "test-session-pathrag"
USER_ID = "test-user"

async def test_agent():
  session_service = InMemorySessionService()
  runner = Runner(
    agent=root_agent,
    app_name="pathrag_spanner_app",
    session_service=session_service,
  )

  session = await session_service.create_session(
    app_name="pathrag_spanner_app",
    user_id=USER_ID,
  )

  queries = [
    "What is PathRAG and how does it work?",
  ]

  for query in queries:
    logger.info(f"Query: {query}")
    content = types.Content(
      role="user",
      parts=[types.Part.from_text(text=query)],
    )

    response = runner.run(
      user_id=USER_ID,
      session_id=session.id,
      new_message=content,
    )

    async for event in response:
      if event.is_final_response():
        final_text = event.content.parts[0].text if event.content and event.content.parts else "(no response)"
        print(f"\n=== Agent Response ===")
        print(final_text)
        print(f"======================\n")

if __name__ == "__main__":
  required_vars = ["GOOGLE_CLOUD_PROJECT", "SPANNER_INSTANCE", "SPANNER_DATABASE"]
  missing = [v for v in required_vars if not os.environ.get(v)]
  if missing:
    logger.error(f"Missing environment variables: {', '.join(missing)}")
  else:
    asyncio.run(test_agent())
