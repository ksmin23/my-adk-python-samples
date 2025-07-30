#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_google_community import BigQueryVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def ingest_documents(project_id: str, location: str, dataset: str, table_name: str, source_dir: str):
  """
  Loads, splits, and embeds documents, then stores them in BigQuery.
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
  embeddings = VertexAIEmbeddings(model_name="text-embedding-005")

  # 4. Initialize BigQueryVectorStore and save data
  print(f"Initializing BigQueryVectorStore and adding documents to table '{dataset}.{table_name}'...")
  vector_store = BigQueryVectorStore(
    project_id=project_id,
    location=location,
    dataset_name=dataset,
    table_name=table_name,
    embedding=embeddings,
  )

  vector_store.add_documents(splits)
  print("Data ingestion complete.")

def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(description="Ingest documents into BigQuery.")
  parser.add_argument(
    "--project_id",
    default=os.getenv("PROJECT_ID"),
    help="GCP project ID. Defaults to PROJECT_ID environment variable.",
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
    default=os.getenv("BIGQUERY_TABLE", "vector_store"),
    help="Table name for storing vectors. Defaults to BIGQUERY_TABLE environment variable or 'vector_store'.",
  )
  parser.add_argument(
    "--source_dir",
    default="../source_documents/",
    help="Directory containing the source text files (e.g., *.txt, *.md). Defaults to ../source_documents/",
  )
  args = parser.parse_args()

  assert args.project_id, "Project ID must be provided via --project_id argument or PROJECT_ID environment variable."
  assert args.location, "Location must be provided via --location argument or LOCATION environment variable."
  assert args.dataset, "Dataset name must be provided via --dataset argument or BIGQUERY_DATASET environment variable."

  ingest_documents(
      project_id=args.project_id,
      location=args.location,
      dataset=args.dataset,
      table_name=args.table_name,
      source_dir=args.source_dir
  )

if __name__ == "__main__":
  main()
