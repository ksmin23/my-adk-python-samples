#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_google_spanner import SpannerVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def ingest_documents(
  instance_id: str, database_id: str, table_name: str, source_dir: str
):
  """
  Loads, splits, and embeds documents, then stores them in Spanner.
  """
  # 0. Create table if not exists
  print(f"Initializing SpannerVectorStore with table '{table_name}'...")
  SpannerVectorStore.init_vector_store_table(
    instance_id=instance_id,
    database_id=database_id,
    table_name=table_name,
    vector_size=768, # Embedding dimension for the text-embedding-005 model
  )

  # 1. Load documents
  print(f"Loading documents from {source_dir}...")
  docs = []
  for glob_pattern in ["**/*.md", "**/*.txt"]:
    loader = DirectoryLoader(source_dir, glob=glob_pattern)
    docs.extend(loader.load())
  print(f"Loaded {len(docs)} documents.")

  # 2. Split documents
  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=100
  )
  splits = text_splitter.split_documents(docs)
  print(f"Split into {len(splits)} chunks.")

  # 3. Initialize embedding model
  print("Initializing VertexAIEmbeddings...")
  embeddings = VertexAIEmbeddings(model_name="text-embedding-005")

  # 4. Initialize Spanner VectorStore and save data
  print(
    f"Initializing SpannerVectorStore and adding documents to table '{table_name}'..."
  )
  SpannerVectorStore.from_documents(
    embedding=embeddings,
    documents=splits,
    instance_id=instance_id,
    database_id=database_id,
    table_name=table_name,
  )
  print("Data ingestion complete.")


def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(description="Ingest documents into Spanner.")
  parser.add_argument(
    "--instance_id",
    default=os.getenv("SPANNER_INSTANCE_ID"),
    help="Spanner instance ID. Defaults to SPANNER_INSTANCE_ID environment variable.",
  )
  parser.add_argument(
    "--database_id",
    default=os.getenv("SPANNER_DATABASE_ID"),
    help="Spanner database ID. Defaults to SPANNER_DATABASE_ID environment variable.",
  )
  parser.add_argument(
    "--table_name",
    default=os.getenv("SPANNER_TABLE_NAME", "vector_store"),
    help="Table name for storing vectors. Defaults to SPANNER_TABLE_NAME environment variable or 'vector_store'.",
  )
  parser.add_argument(
    "--source_dir",
    default="../source_documents/",
    help="Directory containing the source text files (e.g., *.txt, *.md). Defaults to ../source_documents/",
  )
  args = parser.parse_args()

  assert (
    args.instance_id
  ), "Instance ID must be provided via --instance_id argument or SPANNER_INSTANCE_ID environment variable."
  assert (
    args.database_id
  ), "Database ID must be provided via --database_id argument or SPANNER_DATABASE_ID environment variable."

  ingest_documents(
    instance_id=args.instance_id,
    database_id=args.database_id,
    table_name=args.table_name,
    source_dir=args.source_dir,
  )


if __name__ == "__main__":
  main()
