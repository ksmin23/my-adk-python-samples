#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os
import logging
import uuid

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_google_vertexai import VertexAIEmbeddings, VectorSearchVectorStoreDatastore
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ingest_documents(project_id: str, location: str, index_id: str, endpoint_id: str, database: str, kind: str, source_dir: str):
  """
  Loads documents, splits them into chunks, and ingests them into
  Vector Search and Datastore using LangChain's integrated component.
  """
  # 1. Load and split documents
  logging.info(f"Loading documents from {source_dir}...")
  docs = []
  for glob_pattern in ["**/*.md", "**/*.txt"]:
    loader = DirectoryLoader(source_dir, glob=glob_pattern, show_progress=True)
    docs.extend(loader.load())
  logging.info(f"Loaded {len(docs)} documents.")

  logging.info("Splitting documents into chunks...")
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
  chunks = text_splitter.split_documents(docs)
  logging.info(f"Split into {len(chunks)} chunks.")

  # Generate deterministic IDs for each chunk
  namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, 'langchain.document')
  for chunk in chunks:
      chunk.id = str(uuid.uuid5(namespace_uuid, chunk.page_content))

  # 2. Initialize the embedding service
  embedding_model = VertexAIEmbeddings(model_name="text-embedding-005")

  # 3. Initialize VectorSearchVectorStoreDatastore and ingest data
  logging.info("Initializing VectorSearchVectorStoreDatastore...")
  vector_store = VectorSearchVectorStoreDatastore.from_components(
      project_id=project_id,
      region=location,
      index_id=index_id,
      endpoint_id=endpoint_id,
      embedding=embedding_model,
      stream_update=True,
      database=database,
      kind=kind
  )

  logging.info(f"Ingesting {len(chunks)} chunks into Vector Search and Datastore...")
  vector_store.add_documents(chunks, ids=[chunk.id for chunk in chunks])
  logging.info("Data ingestion complete.")


def main():
  """Main function to run the data ingestion process."""
  parser = argparse.ArgumentParser(description="Ingest documents into Datastore and Vertex AI Vector Search using LangChain.")
  parser.add_argument("--project_id", default=os.getenv("PROJECT_ID"), help="GCP project ID.")
  parser.add_argument("--location", default=os.getenv("LOCATION"), help="GCP location for Vertex AI.")
  parser.add_argument("--index_id", required=True, help="Vertex AI Vector Search index ID.")
  parser.add_argument("--endpoint_id", required=True, help="Vertex AI Vector Search endpoint ID.")
  parser.add_argument("--database", default=os.getenv("DATASTORE_DATABASE", "vectorstore"), help="Datastore database ID.")
  parser.add_argument("--kind", default=os.getenv("DATASTORE_KIND", "document_chunk"), help="Datastore kind for storing document chunks.")
  parser.add_argument("--source_dir", help="Directory with source documents.")
  
  args = parser.parse_args()

  if not args.project_id:
    raise ValueError("Project ID must be provided via --project_id or PROJECT_ID environment variable.")

  source_dir = args.source_dir
  if not source_dir:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, '..', 'source_documents')
  
  ingest_documents(
    project_id=args.project_id,
    location=args.location,
    index_id=args.index_id,
    endpoint_id=args.endpoint_id,
    database=args.database,
    kind=args.kind,
    source_dir=source_dir
  )

if __name__ == "__main__":
  main()