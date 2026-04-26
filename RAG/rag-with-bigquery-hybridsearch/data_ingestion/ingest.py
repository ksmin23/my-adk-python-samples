#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os
import time

from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_bigquery_hybridsearch import BigQueryHybridSearchVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Walk up from this script's directory to locate a .env file, so the script
# works regardless of which directory it is invoked from.
load_dotenv(find_dotenv())

def ingest_documents(project_id: str, location: str, dataset: str, table_name: str, source_dir: str):
  """
  Loads, splits, and embeds documents, then stores them in a BigQuery
  hybrid-search table (vector + full-text).
  """

  # 1. Load documents
  print(f"Loading documents from {source_dir}...")
  docs = []
  for glob_pattern in ["**/*.md", "**/*.txt"]:
    loader = DirectoryLoader(source_dir, glob=glob_pattern)
    docs.extend(loader.load())
  print(f"Loaded {len(docs)} documents.")

  # 2. Split documents
  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
  splits = text_splitter.split_documents(docs)
  print(f"Split into {len(splits)} chunks.")

  # 3. Initialize embedding model
  print("Initializing VertexAIEmbeddings...")
  embeddings = VertexAIEmbeddings(model_name="gemini-embedding-001")

  # 4. Initialize BigQueryHybridSearchVectorStore and save data.
  #
  # NOTE: On the very first run, the underlying BigQuery table is created
  # without a schema (the schema is materialized on the first add_documents()
  # call).  The hybrid store's __init__ tries to CREATE SEARCH INDEX in a
  # background thread immediately, which fails with
  #     "Table ... does not have a schema."
  # We therefore add the documents first, then re-instantiate the store so
  # that its post-init hook re-attempts the SEARCH INDEX creation now that
  # the table has a real schema.
  store_kwargs = dict(
    project_id=project_id,
    location=location,
    dataset_name=dataset,
    table_name=table_name,
    embedding=embeddings,
    distance_type="COSINE",
    search_analyzer="LOG_ANALYZER",
    hybrid_search_mode="rrf",
  )

  print(f"Initializing BigQueryHybridSearchVectorStore and adding documents to table '{dataset}.{table_name}'...")
  vector_store = BigQueryHybridSearchVectorStore(**store_kwargs)
  vector_store.add_documents(splits)

  print("Re-initializing the vector store to trigger SEARCH INDEX creation now that the table has a schema...")
  vector_store = BigQueryHybridSearchVectorStore(**store_kwargs)

  # The library kicks off CREATE SEARCH INDEX in a daemon thread; wait for it
  # to finish so the job is actually submitted to BigQuery before we exit.
  timeout_s = 60
  deadline = time.monotonic() + timeout_s
  while vector_store._creating_search_index and time.monotonic() < deadline:
    time.sleep(0.5)
  if vector_store._creating_search_index:
    print(f"WARNING: SEARCH INDEX creation did not finish within {timeout_s}s; "
          "BigQuery may still be building the index in the background.")

  print("Data ingestion complete.")

def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(description="Ingest documents into a BigQuery hybrid-search table.")
  parser.add_argument(
    "--project_id",
    default=os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"),
    help="GCP project ID. Defaults to PROJECT_ID, falling back to GOOGLE_CLOUD_PROJECT environment variable.",
  )
  parser.add_argument(
    "--location",
    default=os.getenv("BIGQUERY_LOCATION"),
    help="BigQuery dataset location. Defaults to BIGQUERY_LOCATION environment variable. (e.g., us)",
  )
  parser.add_argument(
    "--dataset",
    default=os.getenv("BIGQUERY_DATASET"),
    help="BigQuery dataset name. Defaults to BIGQUERY_DATASET environment variable.",
  )
  parser.add_argument(
    "--table_name",
    default=os.getenv("BIGQUERY_TABLE", "hybrid_store"),
    help="Table name for storing vectors and indexed text. Defaults to BIGQUERY_TABLE environment variable or 'hybrid_store'.",
  )
  parser.add_argument(
    "--source_dir",
    help="Directory with source documents.",
  )
  args = parser.parse_args()

  assert args.project_id, "Project ID must be provided via --project_id argument, or PROJECT_ID / GOOGLE_CLOUD_PROJECT environment variable."
  assert args.location, "Location must be provided via --location argument or BIGQUERY_LOCATION environment variable."
  assert args.dataset, "Dataset name must be provided via --dataset argument or BIGQUERY_DATASET environment variable."

  source_dir = args.source_dir
  if not source_dir:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, '..', 'source_documents')

  ingest_documents(
      project_id=args.project_id,
      location=args.location,
      dataset=args.dataset,
      table_name=args.table_name,
      source_dir=source_dir
  )

if __name__ == "__main__":
  main()
