#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
from typing import List

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_community import BigQueryVectorStore
from google.adk.tools import LongRunningFunctionTool

from .deo_optimizer import DEOOptimizer

logger = logging.getLogger(__name__)


def _get_vector_store() -> BigQueryVectorStore:
  """Initialize BigQuery Vector Store with Vertex AI embeddings."""
  return BigQueryVectorStore(
    project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
    location=os.environ["BIGQUERY_LOCATION"],
    dataset_name=os.environ["BIGQUERY_DATASET"],
    table_name=os.environ["BIGQUERY_TABLE"],
    embedding=VertexAIEmbeddings(model_name=os.environ.get("EMBEDDING_MODEL_NAME", "gemini-embedding-001")),
  )


def search_documents_in_bigquery(query: str, k: int = 4) -> str:
  """
  Searches for relevant documents in BigQuery based on a text query.
  Use this tool for standard queries that do NOT contain negation or exclusion intent.

  Args:
      query: The user's search query.
      k: The number of documents to return.

  Returns:
      A formatted string of the retrieved documents.
  """
  try:
    logger.info(f"[Baseline] Searching for: '{query}'")
    vector_store = _get_vector_store()

    retriever = vector_store.as_retriever(
      search_type="similarity",
      search_kwargs={"k": k},
    )

    docs = retriever.invoke(query)

    logger.info(f"[Baseline] Found {len(docs)} documents")
    return "\n\n".join(doc.page_content for doc in docs)
  except Exception as e:
    logger.exception(f"An error occurred while searching in BigQuery: {e}")
    return ""


def deo_search_documents_in_bigquery(
  query: str,
  positives: List[str],
  negatives: List[str],
  k: int = 4,
) -> str:
  """
  Searches for relevant documents in BigQuery using DEO (Direct Embedding Optimization).
  This tool optimizes the query embedding to attract positive intents and repel negative intents
  before searching, enabling negation-aware retrieval.

  Use this tool ONLY when the user's query contains negation or exclusion intent
  (e.g., "excluding X", "without Y", "not about Z").

  Args:
      query: The original user query.
      positives: List of positive sub-queries representing aspects to INCLUDE in retrieval.
                 These should be semantic expansions of the query's core intent.
      negatives: List of negative sub-queries representing aspects to EXCLUDE from retrieval.
                 These should be the explicitly excluded targets and their close synonyms.
      k: The number of documents to return.

  Returns:
      A formatted string of the retrieved documents.
  """
  try:
    logger.info(f"[DEO] Searching for: '{query}'")
    logger.info(f"[DEO] Positives: {positives}")
    logger.info(f"[DEO] Negatives: {negatives}")

    vector_store = _get_vector_store()
    embedding_model = vector_store.embedding

    # DEO: Optimize query embedding
    optimizer = DEOOptimizer(embedding_model)
    optimized_embedding = optimizer.optimize(
      query=query,
      positives=positives,
      negatives=negatives,
    )

    # Search BigQuery with the optimized embedding vector
    docs = vector_store.similarity_search_by_vector(optimized_embedding, k=k)

    logger.info(f"[DEO] Found {len(docs)} documents")
    return "\n\n".join(doc.page_content for doc in docs)
  except Exception as e:
    logger.exception(f"An error occurred during DEO search in BigQuery: {e}")
    return ""


search_documents = LongRunningFunctionTool(func=search_documents_in_bigquery)
deo_search_documents = LongRunningFunctionTool(func=deo_search_documents_in_bigquery)
