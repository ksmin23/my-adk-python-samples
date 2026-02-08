#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Setup script for BigQuery Data Agent with Memory Bank."""
import os
import sys
import argparse
from dotenv import load_dotenv

from memory_bank_customization import (
  create_agent_engine_with_memory_bank,
  update_agent_engine_memory_config,
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
  # Load .env from the agent directory
  script_dir = os.path.dirname(os.path.abspath(__file__))
  project_root = os.path.dirname(script_dir)
  env_path = os.path.join(project_root, "bigquery_data_agent", ".env")
  load_dotenv(env_path)

  parser = argparse.ArgumentParser(description="Setup or update BigQuery Data Agent Memory Bank.")
  parser.add_argument(
    "--project", 
    default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    help="Google Cloud Project ID (default: GOOGLE_CLOUD_PROJECT env)"
  )
  parser.add_argument(
    "--location", 
    default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    help="Google Cloud Location (default: GOOGLE_CLOUD_LOCATION env or 'us-central1')"
  )
  parser.add_argument(
    "--agent_engine_id", 
    default=os.environ.get("AGENT_ENGINE_ID"),
    help="Existing Agent Engine ID to update (default: AGENT_ENGINE_ID env)"
  )
  
  args = parser.parse_args()
  
  project = args.project
  location = args.location
  agent_engine_id = args.agent_engine_id
  
  assert project, "Project ID not set. Please provide --project or set GOOGLE_CLOUD_PROJECT environment variable."
  assert location, "Location not set. Please provide --location or set GOOGLE_CLOUD_LOCATION environment variable."

  try:
    if agent_engine_id:
      logger.info(f"Updating existing Agent Engine: {agent_engine_id}")
      update_agent_engine_memory_config(agent_engine_id, project, location)
      logger.info("✓ Memory Bank configuration updated.")
    else:
      logger.info("Creating new Agent Engine with Memory Bank...")
      agent_id = create_agent_engine_with_memory_bank(project, location)
      logger.info(f"✓ Created Agent Engine: {agent_id}")
      logger.info(f"\nResource ID: {agent_id}")

  except Exception as e:
    logger.error(f"Setup failed: {e}")
    sys.exit(1)


if __name__ == "__main__":
    main()
