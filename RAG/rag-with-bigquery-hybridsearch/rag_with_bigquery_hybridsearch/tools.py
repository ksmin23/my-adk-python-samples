#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_bigquery_hybridsearch import BigQueryHybridSearchVectorStore
from google.adk.tools import LongRunningFunctionTool

logger = logging.getLogger(__name__)


def hybrid_search_documents_in_bigquery(
  query: str,
  text_query: str,
  k: int = 4,
  hybrid_search_mode: str = "rrf",
) -> str:
  """
  Hybrid (vector + full-text) search over documents stored in BigQuery.

  Combines BigQuery VECTOR_SEARCH() (semantic similarity) with SEARCH()
  (full-text keyword matching) using either Reciprocal Rank Fusion ("rrf")
  or keyword pre-filtering ("pre_filter").

  Args:
      query: Natural-language question used for semantic (vector) search.
      text_query: Whitespace-separated keywords used for full-text SEARCH().
          The agent should extract salient nouns, proper nouns, acronyms,
          or code identifiers from the user's question.
      k: Number of documents to return.
      hybrid_search_mode: "rrf" (default) or "pre_filter".

  Returns:
      A string containing the retrieved documents' contents joined by blank lines.
  """
  try:
    logger.info("Initializing BigQuery hybrid search vector store...")
    vector_store = BigQueryHybridSearchVectorStore(
      project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
      location=os.environ["BIGQUERY_LOCATION"],
      dataset_name=os.environ["BIGQUERY_DATASET"],
      table_name=os.environ["BIGQUERY_TABLE"],
      embedding=VertexAIEmbeddings(model_name="gemini-embedding-001"),
      distance_type="COSINE",
      search_analyzer="LOG_ANALYZER",
      hybrid_search_mode="rrf",
    )

    logger.info(
      f"Running hybrid search (mode={hybrid_search_mode}) "
      f"for query='{query}' text_query='{text_query}'..."
    )
    docs = vector_store.hybrid_search(
      query=query,
      text_query=text_query,
      k=k,
      hybrid_search_mode=hybrid_search_mode,
    )

    logger.info(f"Retrieved {len(docs)} documents.")
    return "\n\n".join(doc.page_content for doc in docs)
  except Exception as e:
    logger.exception(f"An error occurred while hybrid-searching in BigQuery: {e}")
    return ""


hybrid_search = LongRunningFunctionTool(func=hybrid_search_documents_in_bigquery)
