#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import argparse
import os

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_google_alloydb_pg import AlloyDBEngine, AlloyDBVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def ingest_documents(database: str, table_name: str, user: str, password: str, source_dir: str):
  """
  Loads, splits, and embeds documents, then stores them in AlloyDB.
  """
  # 1. Load documents
  print(f"Loading documents from {source_dir}...")
  loader = DirectoryLoader(source_dir, glob="**/*.md")
  docs = loader.load()
  print(f"Loaded {len(docs)} documents.")

  # 2. Split documents
  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
  splits = text_splitter.split_documents(docs)
  print(f"Split into {len(splits)} chunks.")

  # 3. Initialize AlloyDB engine
  print("Initializing AlloyDB engine...")
  engine = AlloyDBEngine.from_instance(
    project_id=os.environ["PROJECT_ID"],
    region=os.environ["REGION"],
    cluster=os.environ["CLUSTER"],
    instance=os.environ["INSTANCE"],
    database=database,
    user=user,
    password=password,
  )

  # 4. Initialize embedding model
  print("Initializing VertexAIEmbeddings...")
  embeddings = VertexAIEmbeddings(model_name="text-embedding-005")

  # 5. Initialize AlloyDB VectorStore and save data
  print(f"Initializing AlloyDBVectorStore and adding documents to table '{table_name}'...")
  engine.init_vectorstore_table(
      table_name=table_name,
      vector_size=768, # Embedding dimension for the text-embedding-005 model
      overwrite_existing=True
  )
  vector_store = AlloyDBVectorStore.create_sync(
    engine=engine,
    table_name=table_name,
    embedding_service=embeddings,
  )
  vector_store.add_documents(documents=splits)
  print("Data ingestion complete.")


def main():
  """
  Parses command-line arguments and executes the document ingestion process.
  """
  parser = argparse.ArgumentParser(description="Ingest documents into AlloyDB.")
  parser.add_argument(
    "--database",
    default=os.getenv("DATABASE"),
    help="AlloyDB database name. Defaults to DATABASE environment variable.",
  )
  parser.add_argument(
    "--table_name",
    default=os.getenv("TABLE_NAME", "vector_stores"),
    help="Table name for storing vectors. Defaults to TABLE_NAME environment variable or 'vector_stores'.",
  )
  parser.add_argument(
    "--user",
    default=os.getenv("DB_USER"),
    help="AlloyDB database user. Defaults to DB_USER environment variable.",
  )
  parser.add_argument(
    "--password",
    default=os.getenv("DB_PASSWORD"),
    help="AlloyDB database password. Defaults to DB_PASSWORD environment variable.",
  )
  parser.add_argument(
    "--source_dir",
    default="../source_documents/",
    help="Directory containing the source documents. Defaults to ../source_documents/",
  )
  args = parser.parse_args()

  assert args.database, "Database name must be provided via --database argument or DATABASE environment variable."
  assert args.user, "Database user must be provided via --user argument or DB_USER environment variable."
  assert args.password, "Database password must be provided via --password argument or DB_PASSWORD environment variable."

  ingest_documents(
      database=args.database,
      table_name=args.table_name,
      user=args.user,
      password=args.password,
      source_dir=args.source_dir
  )

if __name__ == "__main__":
  main()
