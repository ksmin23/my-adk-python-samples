#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import atexit
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional

from packaging.version import parse

try:
  import google.adk
except ImportError:
  print(
    "ERROR: Failed to import 'google.adk'. Please install it using 'pip install google-adk'.",
    file=sys.stderr
  )
  sys.exit(1)

# Configure logging at the module level
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(levelname)s - %(message)s",
  stream=sys.stdout,
)

_DOCKERFILE_TEMPLATE = """
FROM python:3.11-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

# Create a non-root user
RUN adduser --disabled-password --gecos "" myuser
RUN chown -R myuser:myuser /app
USER myuser

# Set up environment variables
ENV PATH="/home/myuser/.local/bin:$PATH"
ENV GOOGLE_GENAI_USE_VERTEXAI=1
ENV GOOGLE_CLOUD_PROJECT={gcp_project_id}
ENV GOOGLE_CLOUD_LOCATION={gcp_region}

# Install ADK
RUN pip install google-adk=={adk_version}

# Copy agent source code and install dependencies
COPY "agents/{app_name}/" "/app/agents/{app_name}/"
{install_agent_deps}

{install_custom_adk_script}

EXPOSE {port}

CMD adk {command} --port={port} {host_option} {service_option} {trace_to_cloud_option} "/app/agents"
"""

def _get_default_project_id():
  """Gets the current project ID from the gcloud CLI."""
  try:
    result = subprocess.run(
      ["gcloud", "config", "get-value", "project"],
      capture_output=True,
      text=True,
      check=True,
    )
    return result.stdout.strip()
  except (subprocess.CalledProcessError, FileNotFoundError):
    return None


def _get_service_option(
  adk_version: str,
  session_uri: Optional[str],
  artifact_uri: Optional[str],
  memory_uri: Optional[str],
) -> str:
  """Returns service option string based on adk_version."""
  parsed_version = parse(adk_version)
  assert parsed_version >= parse('1.3.0')
  session_option = (
    f'--session_service_uri={session_uri}' if session_uri else ''
  )
  artifact_option = (
    f'--artifact_service_uri={artifact_uri}' if artifact_uri else ''
  )
  memory_option = f'--memory_service_uri={memory_uri}' if memory_uri else ''
  return f'{session_option} {artifact_option} {memory_option}'


def main():
  """Runs the main deployment logic."""
  default_adk_version = google.adk.__version__

  parser = argparse.ArgumentParser(
    description="Deploy an ADK agent to Google Cloud Run.",
    formatter_class=argparse.RawTextHelpFormatter,
  )
  # Required Arguments
  parser.add_argument(
    "--agent-folder",
    required=True,
    help="Path to the agent source code folder.",
  )
  parser.add_argument(
    "--service-name",
    required=True,
    help="The service name for the Cloud Run deployment.",
  )
  # Options
  parser.add_argument(
    "--project",
    default=_get_default_project_id(),
    help="GCP Project ID. (Default: currently configured gcloud project)",
  )
  parser.add_argument(
    "--region", default="us-central1", help="GCP Region. (Default: us-central1)"
  )
  parser.add_argument(
    "--app-name",
    help="App name. (Default: basename of agent-folder)",
  )
  parser.add_argument(
    "--port", default="8080", help="Port for the server. (Default: 8080)"
  )
  parser.add_argument(
    "--adk-version",
    default=default_adk_version,
    help=f"ADK version to install. (Default: {default_adk_version})",
  )
  parser.add_argument(
    "--adk-cli-path",
    help="Optional. Custom adk cli script path.",
  )
  parser.add_argument(
    "--trace-to-cloud",
    action="store_true",
    help="Optional. Whether to enable Cloud Trace for cloud run.",
  )
  parser.add_argument(
    "--session-service-uri",
    dest="session_service_uri",
    help=("Optional. The URI of the session service."
          "\n- Use 'agentengine://<agent_engine>' to connect to Agent Engine sessions."
          "\n- Use 'sqlite://<path_to_sqlite_file>' to connect to a SQLite DB."
          "\n- Use 'redis://<redis_host>:<port>' to connect to a redis.")
  )
  parser.add_argument(
    "--memory-service-uri",
    dest="memory_service_uri",
    help=("Optional. The URI of the memory service."
          "\n- Use 'rag://<rag_corpus_id>' to connect to Vertex AI Rag Memory Service."
          "\n- Use 'agentengine://<agent_engine>' to connect to Agent Engine sessions.")
  )
  parser.add_argument(
    "--artifact-uri",
    dest="artifact_service_uri",
    help="Optional. The URI of the artifact service, supported URIs: gs://<bucket name> for GCS artifact service.",
  )
  parser.add_argument(
    "--with-ui",
    action="store_true",
    help="Optional. Deploy with the web UI (sets command to 'web').",
  )
  parser.add_argument(
    "--allow-unauthenticated",
    action="store_true",
    help="Optional. Enable allowing unauthenticated access to the service.",
  )
  parser.add_argument(
    "--log-level",
    default="INFO",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    help="Optional. Log level for the gcloud deployment verbosity. (Default: info)"
  )
  # Network Configuration
  parser.add_argument(
    "--vpc-egress",
    default="all-traffic",
    choices=["all-traffic", "private-ranges-only"],
    help="Optional. VPC Egress setting. (Default: all-traffic)"
  )
  parser.add_argument(
    "--vpc-connector",
    help="Optional. Set a VPC connector for this resource."
  )
  parser.add_argument(
    "--network",
    help="Optional. VPC Network for the service."
  )
  parser.add_argument(
    "--subnet",
    help="Optional. VPC Subnet for the service. Requires --network."
  )

  args = parser.parse_args()

  # --- Validate Required Arguments ---
  if not args.project:
    logging.error(
      "GCP Project ID is not set. Please configure it using "
      "'gcloud config set project <PROJECT_ID>' or use the --project option."
    )
    sys.exit(1)

  if args.subnet and not args.network:
    logging.error("--subnet requires --network to be specified.")
    sys.exit(1)

  # --- Main Logic ---
  app_name = args.app_name or os.path.basename(args.agent_folder.rstrip('/'))

  logging.info("--- Deployment Configuration ---")
  logging.info(f"Agent Folder:   {args.agent_folder}")
  logging.info(f"Service Name:   {args.service_name}")
  logging.info(f"App Name:       {app_name}")
  logging.info(f"Project ID:     {args.project}")
  logging.info(f"Region:         {args.region}")
  logging.info(f"Port:           {args.port}")
  logging.info(f"ADK Version:    {args.adk_version}")
  logging.info(f"With UI:        {args.with_ui}")
  logging.info(f"VPC Egress:     {args.vpc_egress}")
  logging.info(f"Network:        {args.network or 'Not specified'}")
  logging.info(f"Subnet:         {args.subnet or 'Not specified'}")
  logging.info("--------------------------------")

  temp_folder = tempfile.mkdtemp(prefix="adk_deploy_")
  # atexit.register(lambda: (logging.info(f"Cleaning up the temp folder: {temp_folder}"), shutil.rmtree(temp_folder)))

  logging.info(f"Start generating Cloud Run source files in {temp_folder}")
  agent_src_path = os.path.join(temp_folder, "agents", app_name)
  os.makedirs(agent_src_path)

  ignore_patterns = None
  ae_ignore_path = os.path.join(args.agent_folder, '.ae_ignore')
  if os.path.exists(ae_ignore_path):
    logging.info(f'Ignoring files matching the patterns in {ae_ignore_path}')
    with open(ae_ignore_path, 'r') as f:
      patterns = [pattern.strip() for pattern in f.readlines()]
      ignore_patterns = shutil.ignore_patterns(*patterns)
  logging.info("Copying agent source code...")
  shutil.copytree(args.agent_folder, agent_src_path, dirs_exist_ok=True, ignore=ignore_patterns)
  logging.info("Copying agent source code complete.")

  install_custom_adk_script = ""
  if args.adk_cli_path:
    logging.info("Copying custom adk script...")
    shutil.copy(args.adk_cli_path, os.path.join(os.path.dirname(agent_src_path), "adk"))
    install_custom_adk_script = (
      "# Copy custom adk script into /home/myuser/.local/bin"
      '''\nCOPY "agents/adk" "/home/myuser/.local/bin/"'''
      # '''\nRUN chmod +x /home/myuser/.local/bin/adk'''
    )
    logging.info("Copying custom adk script complete.")

  install_agent_deps = ""
  if os.path.exists(os.path.join(agent_src_path, "requirements.txt")):
    install_agent_deps = f'RUN pip install -r "/app/agents/{app_name}/requirements.txt"'

  command = "web" if args.with_ui else "api_server"
  host_option = '--host=0.0.0.0' if args.adk_version > '0.5.0' else ''
  service_option = f'--artifact_service_uri={args.artifact_service_uri}' if args.artifact_service_uri else ''
  trace_to_cloud_option = '--trace_to_cloud' if args.trace_to_cloud else ''

  service_option = _get_service_option(
    adk_version=args.adk_version,
    session_uri=args.session_service_uri,
    artifact_uri=args.artifact_service_uri,
    memory_uri=args.memory_service_uri,
  )

  dockerfile_content = _DOCKERFILE_TEMPLATE.format(
    gcp_project_id=args.project,
    gcp_region=args.region,
    adk_version=args.adk_version,
    app_name=app_name,
    install_agent_deps=install_agent_deps,
    install_custom_adk_script=install_custom_adk_script,
    port=args.port,
    command=command,
    host_option=host_option,
    service_option=service_option,
    trace_to_cloud_option=trace_to_cloud_option,
  )

  dockerfile_path = os.path.join(temp_folder, "Dockerfile")
  with open(dockerfile_path, "w", encoding="utf-8") as f:
    f.write(dockerfile_content.strip())  
  logging.info(f"Creating Dockerfile complete: {dockerfile_path}")

  logging.info("Deploying to Cloud Run...")
  try:
    # In gcloud, the verbosity level 'none' is not available.
    gcloud_log_level = args.log_level if args.log_level != "critical" else "error"

    deploy_command = [
      "gcloud", "run", "deploy", args.service_name,
      "--source", temp_folder,
      "--project", args.project,
      "--region", args.region,
      "--port", args.port,
      "--verbosity", gcloud_log_level,
      "--vpc-egress", args.vpc_egress,
    ]
    if args.allow_unauthenticated:
      deploy_command.extend(["--allow-unauthenticated"])
    if args.vpc_connector:
      deploy_command.extend(["--vpc-connector", args.vpc_connector])
    if args.network:
      deploy_command.extend(["--network", args.network])
    if args.subnet:
      deploy_command.extend(["--subnet", args.subnet])
    
    logging.info(f"Executing command:\n{' '.join(deploy_command)}\n")
    subprocess.run(deploy_command, check=True)

    logging.info("Deployment to Cloud Run successful!")

    service_url_command = [
      "gcloud", "run", "services", "describe", args.service_name,
      "--project", args.project,
      "--region", args.region,
      "--format", "value(status.url)",
    ]
    result = subprocess.run(service_url_command, capture_output=True, text=True, check=True)
    logging.info(f"Service URL: {result.stdout.strip()}")

  except subprocess.CalledProcessError as e:
    logging.error(f"Error during gcloud command: {e}")
    sys.exit(1)
  except FileNotFoundError:
    logging.error("'gcloud' command not found. Please ensure the Google Cloud SDK is installed and in your PATH.")
    sys.exit(1)

if __name__ == "__main__":
  main()