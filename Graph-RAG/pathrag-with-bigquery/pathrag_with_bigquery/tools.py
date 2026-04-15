#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import tempfile
import logging

import pathrag_bigquery
from PathRAG import PathRAG, QueryParam

logger = logging.getLogger(__name__)

_rag_instance = None


def get_rag_instance():
  global _rag_instance
  if _rag_instance is None:
    pathrag_bigquery.register()

    _rag_instance = PathRAG(
      working_dir=os.environ.get("PATHRAG_WORKING_DIR", tempfile.mkdtemp(prefix="pathrag_")),
      llm_model_name=os.environ.get("LLM_MODEL_NAME", "gemini/gemini-2.5-flash"),
      embedding_model_name=os.environ.get("EMBEDDING_MODEL_NAME", "gemini/gemini-embedding-001"),
      embedding_dim=int(os.environ.get("EMBEDDING_DIM", "3072")),
      kv_storage="BigQueryKVStorage",
      vector_storage="BigQueryVectorDBStorage",
      graph_storage="BigQueryGraphStorage",
      addon_params={
        "bigquery_project_id": os.environ.get("BIGQUERY_PROJECT", os.environ.get("GOOGLE_CLOUD_PROJECT", "")),
        "bigquery_dataset_id": os.environ.get("BIGQUERY_DATASET"),
        "bigquery_graph_name": os.environ.get("BIGQUERY_GRAPH_NAME", "pathrag_knowledge_graph"),
      },
      # Disable LLM response cache. The cache uses "mode" as the key
      # and stores all cached responses as a nested JSON dict under that
      # key (see handle_cache / save_to_cache in utils.py). On every
      # cache read or write the entire dict must be fetched from the
      # KV store, updated in memory, and written back. This
      # read-modify-write pattern is fine for local JsonKVStorage but
      # adds unnecessary round-trips with a remote backend like BigQuery.
      enable_llm_cache=False,
    )
  return _rag_instance


async def pathrag_tool(query: str) -> str:
  """Queries the PathRAG Knowledge Graph to retrieve relevant context
  using Hybrid Search (Graph + Vector).
  Use this tool when the user asks questions that require knowledge
  from the ingested documents or about specific entities and relationships.

  Args:
    query: The natural language query to ask.

  Returns:
    Retrieved context from the Knowledge Graph including entities,
    relationships, and relevant text chunks.
  """
  logger.debug(f"Querying PathRAG context: {query}")
  try:
    rag = get_rag_instance()
    context = await rag.aquery(
      query,
      param=QueryParam(mode="hybrid", only_need_context=True)
    )
    logger.debug(f"Retrieved context: {context}")
    return str(context) if context else "No relevant context found in the Knowledge Graph."
  except Exception as e:
    import traceback
    traceback.print_exc()
    logger.error(f"Error querying PathRAG: {e}")
    return f"Error querying Knowledge Graph: {str(e)}"
