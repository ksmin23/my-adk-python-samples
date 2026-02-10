#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import argparse
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from PathRAG.PathRAG import QueryParam
from shared_lib.gemini_client import gemini_complete, gemini_embedding
from shared_lib.spanner_storage import SpannerPathRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def insert_document(file_path: str):
  logger.info(f"Ingesting document: {file_path}")
  
  with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

  # Initialize SpannerPathRAG
  # We use a unique working_dir to avoid conflicts if local cache is used, 
  # but primarily we rely on Spanner.
  rag = SpannerPathRAG(
    working_dir="./.pathrag_cache", 
    kv_storage="SpannerKVStorage",
    vector_storage="SpannerVectorStorage",
    graph_storage="SpannerGraphStorage",
    llm_model_func=gemini_complete,
    embedding_func=gemini_embedding,
    llm_model_name="gemini-2.5-flash" # Used in config
  )

  await rag.ainsert(content)
  logger.info("Ingestion complete.")

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Ingest document into PathRAG")
  parser.add_argument("--file", required=True, help="Path to the document file")
  
  args = parser.parse_args()
  
  asyncio.run(insert_document(args.file))
