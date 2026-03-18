#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import tempfile
import logging
from google.adk.tools import tool

from PathRAG import PathRAG, QueryParam

logger = logging.getLogger(__name__)

_rag_instance = None

def get_rag_instance():
  global _rag_instance
  if _rag_instance is None:
    _rag_instance = PathRAG(
      # Required by PathRAG framework for initialization,
      # even though Spanner backends don't use local file storage.
      working_dir=tempfile.mkdtemp(prefix="pathrag_"),
      kv_storage="SpannerKVStorage",
      vector_storage="SpannerVectorDBStorage",
      graph_storage="SpannerGraphStorage",
      llm_model_name="gemini/gemini-2.5-flash",
      embedding_model_name="gemini/gemini-embedding-001",
      embedding_dim=3072,
      addon_params={
        "spanner_instance_id": os.environ.get("SPANNER_INSTANCE"),
        "spanner_database_id": os.environ.get("SPANNER_DATABASE"),
      },
    )
  return _rag_instance


@tool
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
  logger.info(f"Querying PathRAG context: {query}")
  try:
    rag = get_rag_instance()
    context = await rag.aquery(
      query,
      param=QueryParam(mode="hybrid", only_need_context=True)
    )
    return str(context) if context else "No relevant context found in the Knowledge Graph."
  except Exception as e:
    logger.error(f"Error querying PathRAG: {e}")
    return f"Error querying Knowledge Graph: {str(e)}"
