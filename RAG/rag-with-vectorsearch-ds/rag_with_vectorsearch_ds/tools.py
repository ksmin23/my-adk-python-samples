#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
from langchain_google_vertexai import VertexAIEmbeddings, VectorSearchVectorStoreDatastore
from google.adk.tools import LongRunningFunctionTool

logger = logging.getLogger(__name__)

def search_documents_in_vector_search(query: str, k: int = 5) -> str:
  """
  Searches for relevant documents in Vertex AI Vector Search and Datastore.

  Args:
      query: The user's search query.
      k: The number of documents to return.

  Returns:
      A formatted string of the retrieved documents.
  """
  try:
    logger.info("Initializing vector store...")
    vector_store = VectorSearchVectorStoreDatastore.from_components(
      project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
      region=os.environ["GOOGLE_CLOUD_LOCATION"],
      index_id=os.environ["VECTOR_SEARCH_INDEX_ID"],
      endpoint_id=os.environ["VECTOR_SEARCH_ENDPOINT_ID"],
      database=os.environ.get("DATASTORE_DATABASE", "vectorstore"),
      kind=os.environ.get("DATASTORE_KIND", "document_chunk"),
      embedding=VertexAIEmbeddings(model_name="text-embedding-005"),
      stream_update=True
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
    logger.exception(f"An error occurred while searching in Vector Search: {e}")
    return ""

search_documents = LongRunningFunctionTool(func=search_documents_in_vector_search)
