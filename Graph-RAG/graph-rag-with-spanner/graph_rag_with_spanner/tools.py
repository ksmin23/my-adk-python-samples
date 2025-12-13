#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import logging
from langchain_google_spanner import SpannerGraphStore, SpannerGraphVectorContextRetriever
from langchain_google_vertexai import VertexAIEmbeddings
from google.adk.tools import LongRunningFunctionTool

logger = logging.getLogger(__name__)

_graph_store = None

def _get_graph_store():
    global _graph_store
    if _graph_store is None:
        _graph_store = SpannerGraphStore(
            instance_id=os.environ["SPANNER_INSTANCE"],
            database_id=os.environ["SPANNER_DATABASE"],
            graph_name=os.environ["SPANNER_GRAPH_NAME"],
        )
    return _graph_store

def retrieve_graph_context_function(query: str) -> str:
    """
    Retrieves relevant context from the Spanner Graph database based on a query.
    It performs a hybrid search using both vector similarity and graph traversal.
    
    Args:
        query: The user's search query (natural language).
        
    Returns:
        A formatted string containing the Graph Schema and the Retrieved Context (Nodes and Edges).
    """
    try:
        logger.info(f"Retrieving graph context for query: {query}")
        store = _get_graph_store()
        embedding_service = VertexAIEmbeddings(model_name="text-embedding-005")
        
        # Initialize retriever
        # label_expr filters the nodes to start the search from (e.g., "Product")
        label_expr = os.environ.get("SPANNER_SEARCH_LABEL", "Product")
        expand_by_hops = int(os.environ.get("SPANNER_EXPAND_HOPS", "1"))
        
        retriever = SpannerGraphVectorContextRetriever.from_params(
            graph_store=store,
            embedding_service=embedding_service,
            label_expr=label_expr,
            expand_by_hops=expand_by_hops,
            top_k=1, # Number of distinct start nodes to find
            k=10,    # Max neighbor nodes
        )
        
        docs = retriever.invoke(query)
        
        context_str = "\n\n".join(doc.page_content for doc in docs)
        # Assuming store.get_schema property exists as per notebook
        schema_str = store.get_schema 
        
        result = f"Graph Schema: {schema_str}\n\nContext: {context_str}"
        return result

    except Exception as e:
        logger.exception(f"An error occurred while retrieving graph context: {e}")
        return f"Error: {e}"

retrieve_graph_context = LongRunningFunctionTool(func=retrieve_graph_context_function)
