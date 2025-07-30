#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"""Deployment script for the RAG with Spanner Agent."""

import argparse
import logging
import os
import sys

# Add parent directory to path to import the agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
  import vertexai
  from dotenv import load_dotenv
  from rag_with_spanner.agent import root_agent
  from vertexai import agent_engines
  from vertexai.preview.reasoning_engines import AdkApp
except ImportError as e:
  print(f"ERROR: Failed to import necessary libraries. {e}", file=sys.stderr)
  print("Please ensure you have run 'uv pip install -r requirements.txt' and 'uv pip install google-cloud-aiplatform[agent_engines] absl-py'.", file=sys.stderr)
  sys.exit(1)

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s",
  stream=sys.stdout,
)

def create_agent(project_id, location, bucket):
  """Creates and deploys an agent engine."""
  logging.info("Initializing Vertex AI...")
  vertexai.init(project=project_id, location=location, staging_bucket=f"gs://{bucket}")

  # Construct the path to the agent's .env file and load it.
  agent_env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'rag_with_spanner', '.env')
  )

  logging.info(f"Loading agent environment variables from: {agent_env_path}")
  if not os.path.exists(agent_env_path):
    logging.error(f"Agent .env file not found at '{agent_env_path}'.")
    logging.error("Please copy 'rag_with_spanner/.env.example' to 'rag_with_spanner/.env' and fill in the values.")
    sys.exit(1)

  # Load the .env file's values into a dictionary
  from dotenv import dotenv_values
  env_config = dotenv_values(dotenv_path=agent_env_path)

  # Filter for SPANNER_ variables and ensure all required ones are present
  required_vars = [
    "SPANNER_INSTANCE", "SPANNER_DATABASE", "SPANNER_TABLE_NAME"
  ]

  # We only want to pass the SPANNER variables to the agent
  spanner_env_vars = {k: v for k, v in env_config.items() if k.startswith("SPANNER_")}

  # Check for missing keys
  missing_keys = [key for key in required_vars if key not in spanner_env_vars or not spanner_env_vars[key]]
  if missing_keys:
    logging.error(f"Missing required environment variables in {agent_env_path}: {', '.join(missing_keys)}")
    sys.exit(1)

  logging.info("Creating AdkApp...")
  adk_app = AdkApp(agent=root_agent, enable_tracing=True)

  logging.info("Deploying the agent to Agent Engine...")
  remote_agent = agent_engines.create(
    adk_app,
    display_name=root_agent.name,
    requirements=[
      "google-adk==1.5.0",
      "python-dotenv==1.1.1",
      "langchain==0.3.27",
      "langchain-core==0.3.72",
      "langchain-google-vertexai==2.0.27",
      "langchain-google-spanner==0.9.0",
      "google-auth==2.40.3",
      "google-cloud-aiplatform[agent_engines]==1.104.0",
      "google-genai==1.27.0",
      "pydantic==2.11.7",
      "absl-py==2.3.1",
    ],
    env_vars=spanner_env_vars,
    extra_packages=["rag_with_spanner"],
    gcs_dir_name=root_agent.name,
  )
  logging.info(f"Successfully created remote agent: {remote_agent.resource_name}")

def delete_agent(project_id, location, resource_id):
  """Deletes an existing agent engine."""
  logging.info("Initializing Vertex AI...")
  vertexai.init(project=project_id, location=location)

  logging.info(f"Attempting to delete agent with resource ID: {resource_id}")
  remote_agent = agent_engines.get(resource_id)
  remote_agent.delete(force=True)
  logging.info(f"Successfully deleted remote agent: {resource_id}")

def list_all_agents(project_id, location):
  """Lists all agent engines in the project and location."""
  logging.info("Initializing Vertex AI...")
  vertexai.init(project=project_id, location=location)

  logging.info("Fetching list of all remote agents...")
  remote_agents = agent_engines.list()

  if not remote_agents:
    logging.info("No agents found in this project and location.")
    return

  template = '''
- {agent.name} ("{agent.display_name}")
  - Resource ID: {resource_id}
  - Create Time: {agent.create_time}
  - Update Time: {agent.update_time}'''
  
  remote_agents_string = "\n".join(
    template.format(agent=agent, resource_id=agent.name.split('/')[-1]) for agent in remote_agents
  )
  logging.info(f"All remote agents:\n{remote_agents_string}")

def main():
  """Parses arguments and runs the specified deployment action."""
  load_dotenv()

  parser = argparse.ArgumentParser(description="Deploy and manage the RAG with Spanner Agent on Vertex AI Agent Engine.")

  # Common arguments
  parser.add_argument("--project-id", help="GCP Project ID.", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
  parser.add_argument("--location", help="GCP location for deployment.", default=os.getenv("GOOGLE_CLOUD_LOCATION"))
  parser.add_argument("--bucket", help="GCS bucket for staging.", default=os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET"))

  # Action sub-parsers
  subparsers = parser.add_subparsers(dest="action", required=True, help="Action to perform")

  # Create action
  parser_create = subparsers.add_parser("create", help="Creates and deploys a new agent.")

  # Delete action
  parser_delete = subparsers.add_parser("delete", help="Deletes an existing agent.")
  parser_delete.add_argument("--resource-id", required=True, help="The resource ID of the agent to delete.")

  # List action
  parser_list = subparsers.add_parser("list", help="Lists all agents in the project and location.")

  args = parser.parse_args()

  # Validate common arguments
  if not args.project_id:
    logging.error("Missing required argument: --project-id or GOOGLE_CLOUD_PROJECT environment variable.")
    sys.exit(1)
  if not args.location:
    logging.error("Missing required argument: --location or GOOGLE_CLOUD_LOCATION environment variable.")
    sys.exit(1)

  if args.action == "create" and not args.bucket:
    logging.error("Missing required argument for 'create' action: --bucket or GOOGLE_CLOUD_STORAGE_BUCKET environment variable.")
    sys.exit(1)

  # --- Execute Action ---
  logging.info(f"--- {args.action.upper()} Action ---")
  logging.info(f"Project ID: {args.project_id}")
  logging.info(f"Location:   {args.location}")
  if args.action == "create":
    logging.info(f"Staging Bucket: gs://{args.bucket}")
  logging.info("--------------------")

  try:
    if args.action == "create":
      create_agent(args.project_id, args.location, args.bucket)
    elif args.action == "delete":
      delete_agent(args.project_id, args.location, args.resource_id)
    elif args.action == "list":
      list_all_agents(args.project_id, args.location)
  except Exception as e:
    logging.error(f"An error occurred during the '{args.action}' operation: {e}", exc_info=True)
    sys.exit(1)

if __name__ == "__main__":
  main()
