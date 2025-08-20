#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from .prompt import instruction
from .tools import find_restaurants

load_dotenv()

root_agent = LlmAgent(
  model='gemini-2.5-flash',
  name='restaurant_finder_agent',
  description='Helps users find restaurants based on dish names or ingredients.',
  instruction=instruction,
  tools=[
    find_restaurants
  ],
)
