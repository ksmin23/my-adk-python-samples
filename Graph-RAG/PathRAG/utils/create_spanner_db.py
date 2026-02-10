#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import argparse
import logging
from google.cloud import spanner
from google.api_core.exceptions import AlreadyExists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spanner_db(project_id, instance_id, database_id):
  spanner_client = spanner.Client(project=project_id)
  instance = spanner_client.instance(instance_id)

  if not instance.exists():
    logger.error(f"Instance {instance_id} does not exist.")
    return

  database = instance.database(database_id)
  
  # Schema definitions
  ddl_statements = [
    # KV Store
    """CREATE TABLE PathRagKV (
      namespace STRING(MAX),
      key STRING(MAX),
      value JSON,
      embedding ARRAY<FLOAT64>
    ) PRIMARY KEY (namespace, key)""",
    
    # Vector Store
    """CREATE TABLE PathRagVector (
      namespace STRING(MAX),
      id STRING(MAX),
      content STRING(MAX),
      embedding ARRAY<FLOAT64>
    ) PRIMARY KEY (namespace, id)""",
    
    # Graph Nodes
    """CREATE TABLE Nodes (
      node_id STRING(MAX),
      entity_type STRING(MAX),
      description STRING(MAX),
      source_id STRING(MAX)
    ) PRIMARY KEY (node_id)""",
    
    # Graph Edges
    """CREATE TABLE Edges (
      source_node_id STRING(MAX),
      target_node_id STRING(MAX),
      description STRING(MAX),
      keywords STRING(MAX),
      weight FLOAT64
    ) PRIMARY KEY (source_node_id, target_node_id),
      INTERLEAVE IN PARENT Nodes ON DELETE CASCADE""",
    
    # Property Graph
    """CREATE PROPERTY GRAPH PathRagGraph
      NODE TABLES (
        Nodes
      )
      EDGE TABLES (
        Edges
        SOURCE KEY (source_node_id) REFERENCES Nodes (node_id)
        DESTINATION KEY (target_node_id) REFERENCES Nodes (node_id)
      )"""
  ]

  try:
    database.create(ddl_statements=ddl_statements).result(timeout=120)
    logger.info(f"Database {database_id} created successfully.")
  except AlreadyExists:
    logger.info(f"Database {database_id} already exists. Attempting to update schema if needed (not implemented).")
  except Exception as e:
    logger.error(f"Error creating database: {e}")

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Create Spanner Database for PathRAG")
  parser.add_argument("--project_id", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
  parser.add_argument("--instance_id", default=os.environ.get("SPANNER_INSTANCE"))
  parser.add_argument("--database_id", default=os.environ.get("SPANNER_DATABASE"))
  
  args = parser.parse_args()
  
  if not all([args.project_id, args.instance_id, args.database_id]):
    logger.error("Please provide project_id, instance_id, and database_id via arguments or environment variables.")
  else:
    create_spanner_db(args.project_id, args.instance_id, args.database_id)
