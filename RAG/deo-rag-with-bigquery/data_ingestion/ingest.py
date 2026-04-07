#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import glob
import json
import os
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\.cloud\.bigquery")

from dotenv import load_dotenv, find_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_core.documents import Document
from langchain_google_community import BigQueryVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(find_dotenv())

def load_and_split_documents(source_dir: str) -> list[Document]:
  """
  Loads md/txt files from a directory and splits them into chunks.
  """
  print(f"Loading documents from {source_dir}...")
  docs = []
  for glob_pattern in ["**/*.md", "**/*.txt"]:
    loader = DirectoryLoader(source_dir, glob=glob_pattern)
    docs.extend(loader.load())
  print(f"Loaded {len(docs)} documents.")

  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
  splits = text_splitter.split_documents(docs)
  print(f"Split into {len(splits)} chunks.")
  return splits


def load_documents_from_jsonl(source_dir: str) -> list[Document]:
  """
  Finds all JSONL files (with '_id' and 'text' fields) under source_dir and returns Documents.
  """
  jsonl_files = sorted(glob.glob(os.path.join(source_dir, "**", "*.jsonl"), recursive=True))
  if not jsonl_files:
    print(f"No JSONL files found in {source_dir}")
    return []

  print(f"Found {len(jsonl_files)} JSONL file(s) in {source_dir}")
  docs = []
  for jsonl_file in jsonl_files:
    print(f"  Reading {jsonl_file}...")
    with open(jsonl_file, "r", encoding="utf-8") as f:
      for line in f:
        record = json.loads(line)
        doc = Document(
          page_content=record["text"],
          metadata={"_id": record["_id"], "source": jsonl_file},
        )
        docs.append(doc)
  print(f"Loaded {len(docs)} documents.")
  return docs


def add_to_vector_store(
  docs: list[Document],
  project_id: str,
  location: str,
  dataset: str,
  table_name: str,
  batch_size: int = 500,
):
  """
  Embeds documents and stores them in BigQuery VectorStore.
  """
  if not docs:
    print("No documents to ingest.")
    return

  print("Initializing VertexAIEmbeddings...")
  embeddings = VertexAIEmbeddings(model_name=os.environ.get("EMBEDDING_MODEL_NAME", "gemini-embedding-001"))

  print(f"Initializing BigQueryVectorStore and adding documents to table '{dataset}.{table_name}'...")
  vector_store = BigQueryVectorStore(
    project_id=project_id,
    location=location,
    dataset_name=dataset,
    table_name=table_name,
    embedding=embeddings,
  )

  for i in range(0, len(docs), batch_size):
    batch = docs[i:i + batch_size]
    vector_store.add_documents(batch)
    print(f"  Added batch {i // batch_size + 1} ({len(batch)} documents)")
  print("Data ingestion complete.")


def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(description="Ingest documents into BigQuery.")
  parser.add_argument(
    "--project_id",
    default=os.getenv("BIGQUERY_PROJECT_ID"),
    help="GCP project ID. Defaults to BIGQUERY_PROJECT_ID environment variable.",
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
    help="Directory with source documents.",
  )
  parser.add_argument(
    "--mode",
    choices=["documents", "jsonl"],
    default="documents",
    help="Ingestion mode: 'documents' for md/txt files (default), 'jsonl' for JSONL files.",
  )
  parser.add_argument(
    "--batch_size",
    type=int,
    default=500,
    help="Batch size for JSONL ingestion. Defaults to 500.",
  )
  args = parser.parse_args()

  assert args.project_id, "Project ID must be provided via --project_id argument or BIGQUERY_PROJECT_ID environment variable."
  assert args.location, "Location must be provided via --location argument or BIGQUERY_LOCATION environment variable."
  assert args.dataset, "Dataset name must be provided via --dataset argument or BIGQUERY_DATASET environment variable."

  source_dir = args.source_dir
  if not source_dir:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, '..', 'source_documents')

  if args.mode == "jsonl":
    docs = load_documents_from_jsonl(source_dir)
  else:
    docs = load_and_split_documents(source_dir)

  add_to_vector_store(
      docs=docs,
      project_id=args.project_id,
      location=args.location,
      dataset=args.dataset,
      table_name=args.table_name,
      batch_size=args.batch_size,
  )

if __name__ == "__main__":
  main()
