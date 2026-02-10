#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import logging
from typing import Any, Dict
from google.adk.tools import tool

from shared_lib.spanner_storage import SpannerPathRAG
from shared_lib.gemini_client import gemini_complete, gemini_embedding
from PathRAG.PathRAG import QueryParam

logger = logging.getLogger(__name__)

# Singleton instance or per-request? 
# ADK tools are stateless functions usually. 
# But initializing PathRAG might be expensive if it checks DB connectivity every time.
# We'll use a global lazy instance or cached.

_rag_instance = None

def get_rag_instance():
  global _rag_instance
  if _rag_instance is None:
    _rag_instance = SpannerPathRAG(
      working_dir="./.pathrag_cache",
      kv_storage="SpannerKVStorage",
      vector_storage="SpannerVectorStorage",
      graph_storage="SpannerGraphStorage",
      llm_model_func=gemini_complete,
      embedding_func=gemini_embedding,
      llm_model_name="gemini-2.5-flash"
    )
  return _rag_instance

@tool
def query_pathrag_knowledge_graph(query: str) -> str:
  """
  Queries the PathRAG Knowledge Graph to retrieve relevant information using Hybrid Search (Graph + Vector).
  Use this tool when the user asks questions that require knowledge from the ingested documents or about specific entities and relationships.
  
  Args:
    query: The natural language query to ask.
  
  Returns:
    The response from the Knowledge Graph RAG system.
  """
  logger.info(f"Querying PathRAG: {query}")
  try:
    # PathRAG query is async, but ADK tools can be sync or async?
    # Usually we define async def.
    # But tools wrapper handles async?
    return "Async tool required, but defined as sync. Please update to async def if supported."
  except Exception as e:
    logger.error(f"Error querying PathRAG: {e}")
    return f"Error: {str(e)}"

# Redefine as async
@tool
async def query_pathrag_knowledge_graph_async(query: str) -> str:
  """
  Queries the PathRAG Knowledge Graph to retrieve relevant information.
  
  Args:
    query: The natural language query.
  """
  logger.info(f"Querying PathRAG (Async): {query}")
  try:
    rag = get_rag_instance()
    response = await rag.aquery(query, param=QueryParam(mode="hybrid"))
    return str(response)
  except Exception as e:
    logger.error(f"Error querying PathRAG: {e}")
    return f"Error: {str(e)}"

# Export the tool
pathrag_tool = query_pathrag_knowledge_graph_async
