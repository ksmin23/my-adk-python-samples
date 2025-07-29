#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_spanner import SpannerVectorStore
from google.adk.tools import LongRunningFunctionTool

logger = logging.getLogger(__name__)

def search_documents_in_spanner(query: str, k: int = 4) -> str:
  """
  Searches for relevant documents in Spanner based on a query.

  Args:
    query: The user's search query.
    k: The number of documents to return.

  Returns:
    A formatted string of the retrieved documents.
  """
  try:
    logger.info("Connecting to Spanner...")
    vector_store = SpannerVectorStore(
      embedding_service=VertexAIEmbeddings(model_name="text-embedding-005"),
      instance_id=os.environ["SPANNER_INSTANCE_ID"],
      database_id=os.environ["SPANNER_DATABASE_ID"],
      table_name=os.environ["SPANNER_TABLE_NAME"],
    )

    retriever = vector_store.as_retriever(
      search_type="similarity",
      search_kwargs={"k": k},
    )

    logger.info(f"Searching for documents related to '{query}'...")
    docs = retriever.invoke(query)

    logger.info("Processing results...")
    return "\n\n".join(doc.page_content for doc in docs)
  except Exception as e:
    logger.exception(f"An error occurred while searching in Spanner: {e}")
    return ""

search_documents = LongRunningFunctionTool(func=search_documents_in_spanner)
