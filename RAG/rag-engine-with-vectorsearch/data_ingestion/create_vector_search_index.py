#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os

from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

def create_vector_search_index(project_id: str, location: str, index_name: str, embedding_dim: int):
  """
  Creates a new Vertex AI Vector Search index and a public endpoint.

  Args:
    project_id: The GCP project ID.
    location: The GCP location (region).
    index_name: The name for the new index.
    embedding_dim: The dimension of the embeddings (e.g., 768 for text-embedding-005).
  """
  aiplatform.init(project=project_id, location=location)

  # 1. Create the index
  print(f"Creating a new Vector Search index with name: {index_name}")
  my_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name=index_name,
    dimensions=embedding_dim,
    approximate_neighbors_count=10,
    index_update_method="STREAM_UPDATE",
  )
  print(f"Index created: {my_index.resource_name}")
  print(f"Index ID: {my_index.name}")

  # 2. Create an endpoint
  endpoint_name = f"{index_name}-endpoint"
  print(f"Creating a new index endpoint with name: {endpoint_name}")
  my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
    display_name=endpoint_name,
    public_endpoint_enabled=True
  )
  print(f"Endpoint created: {my_index_endpoint.resource_name}")
  print(f"Endpoint ID: {my_index_endpoint.name}")

  # 3. Deploy the index to the endpoint
  deployed_index_id = f"{index_name.replace('-', '_')}_deployed"
  print(f"Deploying index to endpoint with deployed ID: {deployed_index_id}")
  my_index_endpoint.deploy_index(
    index=my_index,
    deployed_index_id=deployed_index_id
  )
  print("Index deployed successfully.")
  print("\n--- Summary ---")
  print(f"Index ID: {my_index.name}")
  print(f"Endpoint ID: {my_index_endpoint.name}")
  print("---------------")


def main():
  """
  Parses command-line arguments and executes the index creation process.
  """
  parser = argparse.ArgumentParser(description="Create a Vertex AI Vector Search index. Note: This process can take 20-30 minutes.")
  parser.add_argument(
    "--project_id",
    default=os.getenv("PROJECT_ID"),
    help="GCP project ID. Defaults to PROJECT_ID environment variable.",
  )
  parser.add_argument(
    "--location",
    default=os.getenv("LOCATION", "us-central1"),
    help="GCP location. Defaults to LOCATION environment variable or 'us-central1'.",
  )
  parser.add_argument(
    "--index_name",
    default=os.getenv("INDEX_NAME"),
    help="The name for the new Vector Search index. Defaults to INDEX_NAME environment variable.",
  )
  parser.add_argument(
    "--embedding_dim",
    type=int,
    default=768,
    help="The dimension of the embeddings. Defaults to 768 (e.g., for text-embedding-005). Please check the dimension of your embedding model.",
  )
  args = parser.parse_args()

  assert args.project_id, "Project ID must be provided via --project_id argument or PROJECT_ID environment variable."
  assert args.location, "Location must be provided via --location argument or LOCATION environment variable."
  assert args.index_name, "Index name must be provided via the --index_name argument or INDEX_NAME environment variable."

  create_vector_search_index(
    project_id=args.project_id,
    location=args.location,
    index_name=args.index_name,
    embedding_dim=args.embedding_dim,
  )

if __name__ == "__main__":
  main()