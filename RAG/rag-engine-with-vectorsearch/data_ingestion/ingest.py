#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os

from dotenv import load_dotenv
from google.cloud import aiplatform
from google.cloud import resourcemanager_v3
from vertexai import rag

load_dotenv()


def ingest_documents(
  project_id: str,
  project_number: str,
  location: str,
  index_id: str,
  endpoint_id: str,
  corpus_display_name: str,
  gcs_source_uri: str,
):
  """
  Creates a RAG Corpus and ingests documents from a GCS URI.
  """
  aiplatform.init(project=project_id, location=location)

  # Construct full resource names for the Vector Search index and endpoint
  index_resource_name = f"projects/{project_number}/locations/{location}/indexes/{index_id}"
  endpoint_resource_name = (
    f"projects/{project_number}/locations/{location}/indexEndpoints/{endpoint_id}"
  )

  # 1. Create a RAG Corpus, linking it to the existing Vector Search index
  print(f"Creating RAG Corpus '{corpus_display_name}'...")
  vector_db = rag.VertexVectorSearch(
    index=index_resource_name, index_endpoint=endpoint_resource_name
  )
  rag_corpus = rag.create_corpus(
    display_name=corpus_display_name,
    backend_config=rag.RagVectorDbConfig(vector_db=vector_db),
  )
  print(f"Successfully created RAG Corpus: {rag_corpus.name}")

  # 2. Import files from GCS into the RAG Corpus
  print(f"Importing files from '{gcs_source_uri}' into corpus...")
  response = rag.import_files(
    corpus_name=rag_corpus.name,
    paths=[gcs_source_uri],
    transformation_config=rag.TransformationConfig(
      chunking_config=rag.ChunkingConfig(
        chunk_size=512,
        chunk_overlap=50,
      )
    ),
  )
  print(f"File import process started. Response: {response}")
  print(
    "Data ingestion complete. It may take a few minutes for the files to be processed and indexed."
  )


def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(
    description="Ingest documents into Google Cloud RAG Engine."
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
    "--index_id",
    required=True,
    help="The ID of the backing Vertex AI Vector Search index.",
  )
  parser.add_argument(
    "--endpoint_id",
    required=True,
    help="The ID of the backing Vertex AI Vector Search endpoint.",
  )
  parser.add_argument(
    "--corpus_display_name",
    required=True,
    help="The display name for the new RAG Corpus.",
  )
  parser.add_argument(
    "--gcs_source_uri",
    required=True,
    help="The GCS URI of the source documents to ingest (e.g., 'gs://my-bucket/docs/').",
  )
  args = parser.parse_args()

  assert (
    args.project_id
  ), "Project ID must be provided via --project_id argument or PROJECT_ID environment variable."
  assert (
    args.location
  ), "Location must be provided via --location argument or LOCATION environment variable."

  # Retrieve project number from project ID
  print(f"Retrieving project number for project ID: {args.project_id}")
  rm_client = resourcemanager_v3.ProjectsClient()
  project_name = f"projects/{args.project_id}"
  project = rm_client.get_project(name=project_name)
  project_number = project.name.split("/")[-1]
  print(f"Successfully retrieved project number: {project_number}")
  return
  ingest_documents(
    project_id=args.project_id,
    project_number=project_number,
    location=args.location,
    index_id=args.index_id,
    endpoint_id=args.endpoint_id,
    corpus_display_name=args.corpus_display_name,
    gcs_source_uri=args.gcs_source_uri,
  )


if __name__ == "__main__":
  main()
