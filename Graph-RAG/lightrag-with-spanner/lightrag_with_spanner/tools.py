#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import tempfile
import logging

import lightrag_spanner
from lightrag import LightRAG, QueryParam
from lightrag.llm.gemini import gemini_embed, gemini_model_complete
from lightrag.utils import EmbeddingFunc

logger = logging.getLogger(__name__)

_rag_instance = None


def _get_embedding_func() -> EmbeddingFunc:
  return EmbeddingFunc(
    embedding_dim=int(os.environ.get("EMBEDDING_DIM", "3072")),
    max_token_size=int(os.environ.get("EMBEDDING_MAX_TOKEN_SIZE", "2048")),
    model_name=os.environ.get("EMBEDDING_MODEL_NAME", "gemini-embedding-001"),
    func=gemini_embed.func,
    send_dimensions=True,
  )


async def get_rag_instance():
  global _rag_instance
  if _rag_instance is None:
    storage_type = os.environ.get("LIGHTRAG_STORAGE_TYPE", "spanner").lower()

    common_params = dict(
      working_dir=os.environ.get("LIGHTRAG_WORKING_DIR", tempfile.mkdtemp(prefix="lightrag_")),
      llm_model_func=gemini_model_complete,
      llm_model_name=os.environ.get("LLM_MODEL_NAME", "gemini-2.5-flash"),
      embedding_func=_get_embedding_func(),
    )

    if storage_type == "spanner":
      lightrag_spanner.register()
      common_params.update(
        kv_storage="SpannerKVStorage",
        vector_storage="SpannerVectorStorage",
        graph_storage="SpannerGraphStorage",
        doc_status_storage="SpannerDocStatusStorage",
        addon_params={
          "spanner_instance_id": os.environ.get("SPANNER_INSTANCE"),
          "spanner_database_id": os.environ.get("SPANNER_DATABASE"),
        },
        # Disable LLM caching -- with remote storage like Spanner, cache lookups
        # add network round-trips on every LLM call with minimal hit rate benefit.
        enable_llm_cache=False,
        enable_llm_cache_for_entity_extract=False,
      )

    rag = LightRAG(**common_params)
    await rag.initialize_storages()
    _rag_instance = rag
  return _rag_instance


async def lightrag_tool(query: str) -> str:
  """Queries the LightRAG Knowledge Graph to retrieve relevant context
  using Hybrid Search (Graph + Vector).
  Use this tool when the user asks questions that require knowledge
  from the ingested documents or about specific entities and relationships.

  Args:
    query: The natural language query to ask.

  Returns:
    Retrieved context from the Knowledge Graph including entities,
    relationships, and relevant text chunks.
  """
  logger.info(f"Querying LightRAG context: {query}")
  try:
    rag = await get_rag_instance()
    context = await rag.aquery(
      query,
      param=QueryParam(mode="hybrid", only_need_context=True)
    )
    logger.info(f"Retrieved context: {context}")
    return str(context) if context else "No relevant context found in the Knowledge Graph."
  except Exception as e:
    import traceback
    traceback.print_exc()
    logger.error(f"Error querying LightRAG: {e}")
    return f"Error querying Knowledge Graph: {str(e)}"
