#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import uuid
import os

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_google_vertexai import VectorSearchVectorStore, VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import vertexai

load_dotenv()


def ingest_documents(
  project_id: str,
  location: str,
  bucket_name: str,
  index_id: str,
  endpoint_id: str,
  source_dir: str,
):
  """
  Loads, splits, and embeds documents, then stores them in Vertex AI Vector Search.
  """
  vertexai.init(project=project_id, location=location)

  # 1. Load documents
  print(f"Loading documents from {source_dir}...")
  docs = []
  for glob_pattern in ["**/*.md", "**/*.txt"]:
    loader = DirectoryLoader(source_dir, glob=glob_pattern, show_progress=True)
    docs.extend(loader.load())
  print(f"Loaded {len(docs)} documents.")

  # 2. Split documents
  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
  splits = text_splitter.split_documents(docs)
  print(f"Split into {len(splits)} chunks.")

  # 3. Generate deterministic IDs for each split
  print("Generating deterministic IDs for document chunks...")
  NAMESPACE_UUID = uuid.uuid5(uuid.NAMESPACE_DNS, 'langchain.document')
  doc_ids = [str(uuid.uuid5(NAMESPACE_UUID, doc.page_content)) for doc in splits]

  # 4. Initialize embedding model
  print("Initializing VertexAIEmbeddings...")
  embeddings = VertexAIEmbeddings(model_name="text-embedding-005")

  # 5. Initialize VectorSearchVectorStore and save data
  print(
    f"Initializing VectorSearchVectorStore and adding documents to index '{index_id}'..."
  )
  vector_store = VectorSearchVectorStore.from_components(
    project_id=project_id,
    region=location,  # In VectorSearchVectorStore, it's region, not location
    gcs_bucket_name=bucket_name,
    index_id=index_id,
    endpoint_id=endpoint_id,
    embedding=embeddings,
    stream_update=True,
  )
  vector_store.add_documents(splits, ids=doc_ids)
  print("Data ingestion complete.")


def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(
    description="Ingest documents into Vertex AI Vector Search."
  )
  parser.add_argument(
    "--project_id",
    default=os.getenv("PROJECT_ID"),
    help="GCP project ID. Defaults to PROJECT_ID environment variable.",
  )
  parser.add_argument(
    "--location",
    default=os.getenv("LOCATION"),
    help="GCP location. Defaults to LOCATION environment variable.",
  )
  parser.add_argument(
    "--bucket_name",
    default=os.getenv("BUCKET_NAME"),
    help="GCS bucket name for Vector Search. Defaults to BUCKET_NAME environment variable.",
  )
  parser.add_argument(
    "--index_id",
    required=True,
    help="Vector Search index ID.",
  )
  parser.add_argument(
    "--endpoint_id",
    required=True,
    help="Vector Search endpoint ID.",
  )
  parser.add_argument(
    "--source_dir",
    default="../source_documents/",
    help="Directory containing the source text files (e.g., *.txt, *.md). Defaults to ../source_documents/",
  )
  args = parser.parse_args()

  assert (
    args.project_id
  ), "Project ID must be provided via --project_id argument or PROJECT_ID environment variable."
  assert (
    args.location
  ), "Location must be provided via --location argument or LOCATION environment variable."
  assert (
    args.bucket_name
  ), "Bucket name must be provided via --bucket_name argument or BUCKET_NAME environment variable."

  ingest_documents(
    project_id=args.project_id,
    location=args.location,
    bucket_name=args.bucket_name,
    index_id=args.index_id,
    endpoint_id=args.endpoint_id,
    source_dir=args.source_dir,
  )


if __name__ == "__main__":
  main()
