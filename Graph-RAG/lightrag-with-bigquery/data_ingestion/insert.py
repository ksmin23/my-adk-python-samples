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

import lightrag_bigquery
from lightrag import LightRAG
from lightrag.llm.gemini import gemini_embed, gemini_model_complete
from lightrag.utils import EmbeddingFunc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BIGQUERY_PROJECT = os.environ.get("BIGQUERY_PROJECT", os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET")
BIGQUERY_GRAPH_NAME = os.getenv("BIGQUERY_GRAPH_NAME", "lightrag_knowledge_graph")
WORKSPACE = os.environ.get("LIGHTRAG_WORKSPACE", "lightrag")

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
  lightrag_bigquery.register()

  return LightRAG(
    working_dir=work_dir,
    workspace=WORKSPACE,
    llm_model_func=gemini_model_complete,
    llm_model_name=os.environ.get("LLM_MODEL_NAME", "gemini-2.5-flash"),
    embedding_func=_get_embedding_func(),
    kv_storage="BigQueryKVStorage",
    vector_storage="BigQueryVectorStorage",
    graph_storage="BigQueryGraphStorage",
    doc_status_storage="BigQueryDocStatusStorage",
    addon_params={
      "bigquery_project_id": BIGQUERY_PROJECT,
      "bigquery_dataset_id": BIGQUERY_DATASET,
      "bigquery_graph_name": BIGQUERY_GRAPH_NAME,
    },
    enable_llm_cache=False,
    enable_llm_cache_for_entity_extract=False,
  )


def _get_working_dir() -> str:
  return os.environ.get("LIGHTRAG_WORKING_DIR") or tempfile.mkdtemp(prefix="lightrag_")


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

  required_vars = ["GOOGLE_GENAI_USE_VERTEXAI", "BIGQUERY_DATASET"]
  missing = [v for v in required_vars if not os.environ.get(v)]
  if missing:
    logger.error(f"Missing environment variables: {', '.join(missing)}")
  elif args.sample:
    asyncio.run(insert_sample_docs())
  elif args.file:
    asyncio.run(insert_document(args.file))
  else:
    parser.error("Either --file or --sample is required.")
