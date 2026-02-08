#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import logging
import sys

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest

# Set up a general handler for all logs to be printed in your Colab output.
# We'll set the overall level to INFO.
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  stream=sys.stdout
)

# Get the specific logger used by ADK.
logger = logging.getLogger('google_adk')


def log_system_instructions(callback_context: CallbackContext, llm_request: LlmRequest):
  """A callback to print the LLM request."""
  logger.info(
    f"\n*System Instruction*:\n{llm_request.config.system_instruction}\n*********\n"
  )


def log_tool_call(tool, args, tool_response, **kwargs):
  """A callback to print the LLM request."""
  logger.info(f"\n*Tool*:\n{tool}")
  logger.info(f"\n*Tool call*:\n{args}")
  logger.info(f"\n*Tool response*:\n{tool_response}\n*********\n")
