#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv
import os

from google.adk.agents.llm_agent import Agent
from google.adk.apps.app import App
from google.adk.plugins.bigquery_logging_plugin import BigQueryAgentAnalyticsPlugin

from .prompt import instruction
from .tools import get_weather, get_current_time

load_dotenv()

APP_NAME = "weather_app"

root_agent = Agent(
  model="gemini-2.5-flash",
  name="weather_and_time_agent",
  description="Tells the current time and weather in a specified city.",
  instruction=instruction,
  tools=[get_weather, get_current_time]
)

app = App(
  name=APP_NAME,
  root_agent=root_agent,
  plugins=[
    BigQueryAgentAnalyticsPlugin(
      # NOTE: project_id and dataset_id are mandatory.
      project_id=os.getenv('GOOGLE_CLOUD_PROJECT'),
      dataset_id=os.getenv('BIGQUERY_DATASET', 'test_dataset'),
      table_id=os.getenv('BIGQUERY_TABLE', 'agent_events'),
    ),
  ],
)
