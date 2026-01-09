#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
from google.cloud import vectorsearch_v1beta
from google.adk.tools import LongRunningFunctionTool


logger = logging.getLogger(__name__)


def search_documents_in_vector_search(query: str, k: int = 5) -> str:
  """
  Searches for relevant documents in Vertex AI Vector Search 2.0 (Hybrid Search).
  Uses both Semantic Search and Text Search combined with RRF.

  Args:
      query: The user's search query.
      k: The number of documents to return.

  Returns:
      A formatted string of the retrieved documents, or empty string if no results.
  """

  logger.debug(f"[Tool:search_documents] Start - query: '{query}'")
  try:
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ["GOOGLE_CLOUD_LOCATION"]
    collection_name = os.environ["VECTOR_SEARCH_COLLECTION_NAME"]

    # Initialize Client (no need for client_options with regional endpoint)
    logger.debug(f"[Tool:search_documents] Initializing Vector Search Client...")
    data_object_search_service_client = vectorsearch_v1beta.DataObjectSearchServiceClient()

    # Define Hybrid Search Request (Semantic + Text)
    # Combining results using Reciprocal Rank Fusion (RRF)
    parent = f"projects/{project_id}/locations/{location}/collections/{collection_name}"

    logger.debug(f"[Tool:search_documents] Defining Hybrid Search Request...")
    batch_search_request = vectorsearch_v1beta.BatchSearchDataObjectsRequest(
      parent=parent,
      searches=[
        # 1. Semantic Search
        vectorsearch_v1beta.Search(
          semantic_search=vectorsearch_v1beta.SemanticSearch(
            search_text=query,
            search_field="dense_vector",  # Vector field defined in Collection Schema
            task_type="QUESTION_ANSWERING",  # Optimized for retrieval
            top_k=k * 2,  # Fetch more for RRF to re-rank
            output_fields=vectorsearch_v1beta.OutputFields(
              data_fields=["content"]
            ),
          )
        ),
        # 2. Text Search (Keyword)
        vectorsearch_v1beta.Search(
          text_search=vectorsearch_v1beta.TextSearch(
            search_text=query,
            data_field_names=["content"],  # Data field for text search
            top_k=k * 2,
            output_fields=vectorsearch_v1beta.OutputFields(
              data_fields=["content"]
            ),
          )
        ),
      ],
      combine=vectorsearch_v1beta.BatchSearchDataObjectsRequest.CombineResultsOptions(
        ranker=vectorsearch_v1beta.Ranker(
          rrf=vectorsearch_v1beta.ReciprocalRankFusion(weights=[1.0, 1.0])
        )
      ),
    )

    logger.debug(f"[Tool:search_documents] API Call - Performing Hybrid Search for '{query}'...")
    batch_results = data_object_search_service_client.batch_search_data_objects(
      batch_search_request
    )

    # Process Results
    # When a ranker is used, batch_results.results contains a single ranked list
    # results[0] is the SearchDataObjectsResponse with the combined RRF-ranked results
    if not batch_results.results:
      logger.debug(f"[Tool:search_documents] No batch results found for '{query}'")
      return ""

    combined_results = batch_results.results[0]

    if not combined_results.results:
      logger.debug(f"[Tool:search_documents] No combined results found for '{query}'")
      return ""

    # Extract content directly from search results
    results = []
    for result in combined_results.results[:k]:
      data = result.data_object.data
      content = data["content"] if data else ""
      if content:
        results.append(content)

    return "\n\n".join(results)

  except Exception as e:
    logger.error(f"[Tool:search_documents] An error occurred while searching in Vector Search: {e}")
    return ""


search_documents = LongRunningFunctionTool(func=search_documents_in_vector_search)
