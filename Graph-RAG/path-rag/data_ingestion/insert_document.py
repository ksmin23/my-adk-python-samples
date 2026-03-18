#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import argparse
import asyncio
import tempfile
import shutil
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from PathRAG import PathRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPANNER_INSTANCE = os.environ.get("SPANNER_INSTANCE")
SPANNER_DATABASE = os.environ.get("SPANNER_DATABASE")

async def insert_document(file_path: str):
  logger.info(f"Ingesting document: {file_path}")

  with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

  work_dir = tempfile.mkdtemp(prefix="pathrag_")
  try:
    rag = PathRAG(
      # Required by PathRAG framework for initialization,
      # even though Spanner backends don't use local file storage.
      working_dir=work_dir,
      kv_storage="SpannerKVStorage",
      vector_storage="SpannerVectorDBStorage",
      graph_storage="SpannerGraphStorage",
      llm_model_name="gemini/gemini-2.5-flash",
      embedding_model_name="gemini/gemini-embedding-001",
      embedding_dim=3072,
      addon_params={
        "spanner_instance_id": SPANNER_INSTANCE,
        "spanner_database_id": SPANNER_DATABASE,
      },
    )

    await rag.ainsert(content)
    logger.info("Ingestion complete.")
  finally:
    shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Ingest document into PathRAG")
  parser.add_argument("--file", required=True, help="Path to the document file")

  args = parser.parse_args()

  required_vars = ["SPANNER_INSTANCE", "SPANNER_DATABASE", "GEMINI_API_KEY"]
  missing = [v for v in required_vars if not os.environ.get(v)]
  if missing:
    logger.error(f"Missing environment variables: {', '.join(missing)}")
  else:
    asyncio.run(insert_document(args.file))
