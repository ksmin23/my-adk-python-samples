#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os
import time

from google.cloud import vectorsearch_v1beta
from dotenv import load_dotenv

load_dotenv()


def create_collection(
  project_id: str,
  location: str,
  collection_name: str,
  embedding_model: str = "gemini-embedding-001",
  embedding_dim: int = 768,
  create_index: bool = True,
  wait_for_index: bool = False
):
  """
  Creates a new Vertex AI Vector Search 2.0 Collection with optional ANN Index.

  The collection uses the Vector Search 2.0 dict-based schema format,
  following the official SDK patterns.

  Args:
      project_id: GCP Project ID
      location: GCP Location
      collection_name: Collection name
      embedding_model: Embedding model ID (default: gemini-embedding-001)
      embedding_dim: Embedding dimensions (768 for gemini-embedding-001)
      create_index: Whether to create an ANN index after collection creation
      wait_for_index: Whether to wait for index creation to complete
  """
  # Initialize the client
  vector_search_client = vectorsearch_v1beta.VectorSearchServiceClient()

  parent = f"projects/{project_id}/locations/{location}"

  print(f"Creating Collection: {collection_name} in {parent}")

  # Create Collection using dict-based schema format (as shown in the notebook)
  # This is the recommended approach for Vector Search 2.0
  request = vectorsearch_v1beta.CreateCollectionRequest(
    parent=parent,
    collection_id=collection_name,
    collection={
      # Data Schema: Define the structure of your data
      "data_schema": {
        "type": "object",
        "properties": {
          "content": {"type": "string"},  # Document content for text search
        },
      },
      # Vector Schema: Define embedding fields with auto-embedding config
      "vector_schema": {
        # Named vector field for semantic search
        # Using text_template to auto-generate embeddings from content
        "dense_vector": {
          "dense_vector": {
            "dimensions": embedding_dim,
            "vertex_embedding_config": {
              "model_id": embedding_model,
              "text_template": "{content}",  # Auto-embed from content field
              "task_type": "RETRIEVAL_DOCUMENT",
            },
          },
        },
      },
    }
  )

  try:
    operation = vector_search_client.create_collection(request=request)
    print("Waiting for collection creation to complete...")
    response = operation.result()
    print(f"✅ Collection created successfully: {response.name}")
    print(f"\nCollection Details:")
    print(f"  - Data Schema: content (string)")
    print(f"  - Vector Schema: dense_vector (auto-embedding with {embedding_model})")
    print(f"  - Embedding Dimensions: {embedding_dim}")

    # Create ANN Index if requested
    if create_index:
      create_ann_index(
        vector_search_client,
        project_id,
        location,
        collection_name,
        wait_for_index
      )

    return response
  except Exception as e:
    print(f"Error creating collection: {e}")
    raise


def create_ann_index(
  client: vectorsearch_v1beta.VectorSearchServiceClient,
  project_id: str,
  location: str,
  collection_name: str,
  wait_for_completion: bool = False
):
  """
  Creates an ANN (Approximate Nearest Neighbor) Index on the dense_vector field.

  ANN indexes provide blazingly fast similarity search at production scale,
  using Google's ScaNN algorithm.

  Args:
      client: VectorSearchServiceClient instance
      project_id: GCP Project ID
      location: GCP Location
      collection_name: Collection name
      wait_for_completion: Whether to wait for index creation to complete
  """
  parent = f"projects/{project_id}/locations/{location}/collections/{collection_name}"
  index_id = "dense-vector-index"

  print(f"\n🔨 Creating ANN Index: {index_id}")

  request = vectorsearch_v1beta.CreateIndexRequest(
    parent=parent,
    index_id=index_id,
    index={
      "index_field": "dense_vector",  # Index the dense vector field
      "store_fields": ["content"],  # Store content for quick retrieval
    },
  )

  try:
    operation = client.create_index(request)
    operation_name = operation.operation.name
    print(f"   LRO: {operation_name}")
    print(f"   Index creation started. This typically takes 5-30 minutes.")

    if wait_for_completion:
      print("\n⏳ Waiting for index creation to complete...")
      poll_interval = 60  # Check every 60 seconds

      while not operation.done():
        print(f"   Still creating... (checking every {poll_interval} seconds)")
        time.sleep(poll_interval)

      print("✅ ANN Index created successfully!")
      print(f"   Index: {parent}/indexes/{index_id}")
    else:
      print("\n💡 To check index status, run:")
      print(f"   gcloud ai vector-search indexes describe {index_id} \\")
      print(f"     --collection={collection_name} \\")
      print(f"     --project={project_id} \\")
      print(f"     --location={location}")

    return operation

  except Exception as e:
    if "already exists" in str(e).lower():
      print(f"   ℹ️ Index '{index_id}' already exists.")
    else:
      print(f"   ⚠️ Error creating index: {e}")
    return None


def main():
  parser = argparse.ArgumentParser(
    description="Create a Vertex AI Vector Search 2.0 Collection with ANN Index."
  )
  parser.add_argument(
    "--project_id",
    default=os.getenv("GOOGLE_CLOUD_PROJECT"),
    help="GCP Project ID (default: from GOOGLE_CLOUD_PROJECT env var)"
  )
  parser.add_argument(
    "--location",
    default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    help="GCP Location (default: from GOOGLE_CLOUD_LOCATION env var or 'us-central1')"
  )
  parser.add_argument(
    "--collection_name",
    default=os.getenv("VECTOR_SEARCH_COLLECTION_NAME"),
    help="Collection Name (default: from VECTOR_SEARCH_COLLECTION_NAME env var)"
  )
  parser.add_argument(
    "--embedding_model",
    default="gemini-embedding-001",
    help="Embedding model ID (default: gemini-embedding-001)"
  )
  parser.add_argument(
    "--embedding_dim",
    type=int,
    default=768,
    help="Embedding dimensions (768 for gemini-embedding-001)"
  )
  parser.add_argument(
    "--no-index",
    action="store_true",
    help="Skip ANN index creation"
  )
  parser.add_argument(
    "--wait-for-index",
    action="store_true",
    help="Wait for ANN index creation to complete"
  )

  args = parser.parse_args()

  if not args.project_id or not args.collection_name:
    raise ValueError("Project ID and Collection Name must be provided.")

  create_collection(
    args.project_id,
    args.location,
    args.collection_name,
    args.embedding_model,
    args.embedding_dim,
    create_index=not args.no_index,
    wait_for_index=args.wait_for_index
  )


if __name__ == "__main__":
  main()
