#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import logging
import sys

# Set up a general handler for all logs to be printed in your Colab output.
# We'll set the overall level to INFO.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Get the specific logger used by ADK.
logger = logging.getLogger('google_adk')

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import Agent
from google.adk.tools.preload_memory_tool import preload_memory_tool
from google.adk.tools.load_memory_tool import load_memory_tool
from .log_tools import log_system_instructions, log_tool_call


async def auto_save_session_to_memory_callback(callback_context: CallbackContext):
  # Use the invocation context to access the conversation history that should
  # be used as the data source for memory generation.
  inv_ctx = getattr(callback_context, "_invocation_context")
  memory_service = inv_ctx.memory_service
  if not memory_service:
    logger.warning("⚠️ Memory Service not set, cannot save to memory")
    return

  await memory_service.add_session_to_memory(
    inv_ctx.session
  )
  logger.info("\n****Triggered memory generation****\n")


root_agent = Agent(
  model='gemini-2.5-flash',
  name='Generic_QA_Agent',
  description='A helpful assistant for user questions.',
  instruction='Answer user questions to the best of your knowledge',
  tools=[
    preload_memory_tool, # PreloadMemoryTool retrieves memories will be appended to the System Instructions.
    load_memory_tool # Unlike PreloadMemoryTool, LoadMemoryTool acts like a standard tool.
                     # The agent needs to decide whether the tool should be invoked
  ],
  before_model_callback=log_system_instructions,
  after_tool_callback=log_tool_call,
  after_agent_callback=auto_save_session_to_memory_callback,
)
