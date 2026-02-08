#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Setup script for BigQuery Data Agent with Memory Bank."""
import os
import sys
import logging
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
    
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    existing_id = os.environ.get("AGENT_ENGINE_ID")
    
    if not project:
        logger.error("GOOGLE_CLOUD_PROJECT not set in environment or .env file.")
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
            logger.info(f"\nAdd to your .env file: AGENT_ENGINE_ID={agent_id}")
            
            # Optionally update .env automatically if it exists
            env_file = ".env"
            if os.path.exists(env_file):
                with open(env_file, "a") as f:
                    f.write(f"\n# Agent Engine ID for Memory Bank\nAGENT_ENGINE_ID={agent_id}\n")
                logger.info(f"✓ Added AGENT_ENGINE_ID to {env_file}")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
