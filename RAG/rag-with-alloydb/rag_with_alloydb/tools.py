#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import logging
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_alloydb_pg import AlloyDBEngine, AlloyDBVectorStore
from google.adk.tools import LongRunningFunctionTool

logger = logging.getLogger(__name__)

def search_documents_in_alloydb(query: str, k: int = 4) -> str:
  """
  Searches for relevant documents in AlloyDB based on a query.

  Args:
      query: The user's search query.
      k: The number of documents to return.

  Returns:
      A formatted string of the retrieved documents.
  """
  try:
    logger.info("Connecting to AlloyDB...")
    engine = AlloyDBEngine.from_instance(
      project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
      region=os.environ["ALLOYDB_REGION"],
      cluster=os.environ["ALLOYDB_CLUSTER"],
      instance=os.environ["ALLOYDB_INSTANCE"],
      database=os.environ["ALLOYDB_DATABASE"],
      user=os.environ["ALLOYDB_USER"],
      password=os.environ["ALLOYDB_PASS"],
    )

    logger.info("Initializing vector store...")
    vector_store = AlloyDBVectorStore.create_sync(
        engine=engine,
        table_name=os.environ["ALLOYDB_TABLE_NAME"],
        embedding_service=VertexAIEmbeddings(model_name="text-embedding-005"),
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
    logger.exception(f"An error occurred while searching in AlloyDB: {e}")
    return ""

search_documents = LongRunningFunctionTool(func=search_documents_in_alloydb)
