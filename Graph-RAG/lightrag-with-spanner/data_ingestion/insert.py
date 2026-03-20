#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import argparse
import asyncio
import tempfile
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import lightrag_spanner
from lightrag import LightRAG
from lightrag.llm.gemini import gemini_embed, gemini_model_complete
from lightrag.utils import EmbeddingFunc

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


def _get_embedding_func() -> EmbeddingFunc:
  return EmbeddingFunc(
    embedding_dim=int(os.environ.get("EMBEDDING_DIM", "3072")),
    max_token_size=int(os.environ.get("EMBEDDING_MAX_TOKEN_SIZE", "2048")),
    model_name=os.environ.get("EMBEDDING_MODEL_NAME", "gemini-embedding-001"),
    func=gemini_embed.func,
    send_dimensions=True,
  )


def _create_rag_instance(work_dir: str) -> LightRAG:
  storage_type = os.environ.get("LIGHTRAG_STORAGE_TYPE", "spanner").lower()

  common_params = dict(
    working_dir=work_dir,
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
        "spanner_instance_id": SPANNER_INSTANCE,
        "spanner_database_id": SPANNER_DATABASE,
      },
      enable_llm_cache=False,
      enable_llm_cache_for_entity_extract=False,
    )

  return LightRAG(**common_params)


def _get_working_dir() -> str:
  storage_type = os.environ.get("LIGHTRAG_STORAGE_TYPE", "spanner").lower()
  working_dir = os.environ.get("LIGHTRAG_WORKING_DIR")

  if storage_type != "spanner" and not working_dir:
    raise ValueError(
      "LIGHTRAG_WORKING_DIR environment variable is required "
      "when LIGHTRAG_STORAGE_TYPE is not 'spanner'."
    )

  return working_dir or tempfile.mkdtemp(prefix="lightrag_")


async def insert_document(file_path: str):
  logger.info(f"Ingesting document: {file_path}")

  with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

  work_dir = _get_working_dir()
  rag = _create_rag_instance(work_dir)
  await rag.initialize_storages()
  await rag.ainsert(content)
  logger.info("Ingestion complete.")


async def insert_sample_docs():
  logger.info(f"Ingesting {len(SAMPLE_DOCS)} sample documents...")

  work_dir = _get_working_dir()
  rag = _create_rag_instance(work_dir)
  await rag.initialize_storages()
  await rag.ainsert(SAMPLE_DOCS)
  logger.info("Sample documents ingestion complete.")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Ingest document into LightRAG")
  parser.add_argument("--file", help="Path to the document file")
  parser.add_argument("--sample", action="store_true", help="Ingest sample documents")

  args = parser.parse_args()

  storage_type = os.environ.get("LIGHTRAG_STORAGE_TYPE", "spanner").lower()
  required_vars = ["GEMINI_API_KEY"]
  if storage_type == "spanner":
    required_vars += ["SPANNER_INSTANCE", "SPANNER_DATABASE"]
  else:
    required_vars += ["LIGHTRAG_WORKING_DIR"]
  missing = [v for v in required_vars if not os.environ.get(v)]
  if missing:
    logger.error(f"Missing environment variables: {', '.join(missing)}")
  elif args.sample:
    asyncio.run(insert_sample_docs())
  elif args.file:
    asyncio.run(insert_document(args.file))
  else:
    parser.error("Either --file or --sample is required.")
