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

SAMPLE_DOCS = [
    """
    Apple Inc. is an American multinational technology company headquartered in
    Cupertino, California. Apple was founded on April 1, 1976, by Steve Jobs,
    Steve Wozniak, and Ronald Wayne. The company designs, develops, and sells
    consumer electronics, computer software, and online services.
    Tim Cook has been the CEO of Apple since August 2011, succeeding Steve Jobs.
    Under Cook's leadership, Apple launched Apple Watch, AirPods, and Apple Vision Pro.
    """,
    """
    Steve Jobs was an American business magnate, inventor, and investor. He was
    the co-founder, chairman, and CEO of Apple Inc. Jobs also co-founded and
    served as the chairman of Pixar Animation Studios. He was a board member at
    The Walt Disney Company following the acquisition of Pixar by Disney.
    Jobs is widely recognized as a pioneer of the personal computer revolution
    and for his influential career in the computer and consumer electronics fields.
    """,
    """
    Google LLC is an American multinational corporation and technology company
    focusing on online advertising, search engine technology, cloud computing,
    and artificial intelligence. Sundar Pichai has been the CEO of Google since
    October 2015 and of its parent company Alphabet Inc. since December 2019.
    Google was founded on September 4, 1998, by Larry Page and Sergey Brin
    while they were Ph.D. students at Stanford University in California.
    """,
]


def _create_rag_instance(work_dir: str) -> PathRAG:
  storage_type = os.environ.get("PATHRAG_STORAGE_TYPE", "spanner").lower()

  common_params = dict(
    working_dir=work_dir,
    llm_model_name="gemini/gemini-2.5-flash",
    embedding_model_name="gemini/gemini-embedding-001",
    embedding_dim=3072,
  )

  if storage_type == "spanner":
    common_params.update(
      kv_storage="SpannerKVStorage",
      vector_storage="SpannerVectorDBStorage",
      graph_storage="SpannerGraphStorage",
      addon_params={
        "spanner_instance_id": SPANNER_INSTANCE,
        "spanner_database_id": SPANNER_DATABASE,
      },
      # Disable LLM response cache. The cache uses "mode" as the key
      # and stores all cached responses as a nested JSON dict under that
      # key (see handle_cache / save_to_cache in utils.py). On every
      # cache read or write the entire dict must be fetched from the
      # KV store, updated in memory, and written back. This
      # read-modify-write pattern is fine for local JsonKVStorage but
      # adds unnecessary round-trips with a remote backend like Spanner.
      enable_llm_cache=False,
    )
  else:
    common_params.update(
      kv_storage="JsonKVStorage",
      vector_storage="NanoVectorDBStorage",
      graph_storage="NetworkXStorage",
    )

  return PathRAG(**common_params)


def _get_working_dir() -> str:
  storage_type = os.environ.get("PATHRAG_STORAGE_TYPE", "spanner").lower()
  working_dir = os.environ.get("PATHRAG_WORKING_DIR")

  if storage_type != "spanner" and not working_dir:
    raise ValueError(
      "PATHRAG_WORKING_DIR environment variable is required "
      "when PATHRAG_STORAGE_TYPE is not 'spanner'."
    )

  return working_dir or tempfile.mkdtemp(prefix="pathrag_")


async def insert_document(file_path: str):
  logger.info(f"Ingesting document: {file_path}")

  with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

  work_dir = _get_working_dir()
  rag = _create_rag_instance(work_dir)
  await rag.ainsert(content)
  logger.info("Ingestion complete.")


async def insert_sample_docs():
  logger.info(f"Ingesting {len(SAMPLE_DOCS)} sample documents...")

  work_dir = _get_working_dir()
  rag = _create_rag_instance(work_dir)
  await rag.ainsert(SAMPLE_DOCS)
  logger.info("Sample documents ingestion complete.")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Ingest document into PathRAG")
  parser.add_argument("--file", help="Path to the document file")
  parser.add_argument("--sample", action="store_true", help="Ingest sample documents")

  args = parser.parse_args()

  storage_type = os.environ.get("PATHRAG_STORAGE_TYPE", "spanner").lower()
  required_vars = ["GEMINI_API_KEY"]
  if storage_type == "spanner":
    required_vars += ["SPANNER_INSTANCE", "SPANNER_DATABASE"]
  else:
    required_vars += ["PATHRAG_WORKING_DIR"]
  missing = [v for v in required_vars if not os.environ.get(v)]
  if missing:
    logger.error(f"Missing environment variables: {', '.join(missing)}")
  elif args.sample:
    asyncio.run(insert_sample_docs())
  elif args.file:
    asyncio.run(insert_document(args.file))
  else:
    parser.error("Either --file or --sample is required.")
