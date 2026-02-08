#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Setup script for BigQuery Data Agent with Memory Bank."""
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the project root to sys.path
# Now setup_memory_bank.py is in utils/, so project root is one level up
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from .memory_config import (
  create_agent_engine_with_memory_bank,
  update_agent_engine_memory_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
  load_dotenv()
  
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
  existing_id = args.agent_engine_id
  
  if not project:
    logger.error("Project ID not set. Please provide --project or set GOOGLE_CLOUD_PROJECT environment variable.")
    sys.exit(1)
    
    try:
        if existing_id:
            logger.info(f"Updating existing Agent Engine: {existing_id}")
            update_agent_engine_memory_config(existing_id, project, location)
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
