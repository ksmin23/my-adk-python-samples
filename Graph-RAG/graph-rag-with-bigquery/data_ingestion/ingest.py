#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import copy
import argparse
import requests
import zipfile
import shutil
from typing import List
from dotenv import find_dotenv, load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_bigquery_graph import BigQueryGraphStore
from google.cloud import bigquery
import tqdm

load_dotenv(find_dotenv())

def download_and_unzip(url: str, extract_to: str):
    print(f"Downloading data from {url}...")
    response = requests.get(url, stream=True)
    zip_path = os.path.join(extract_to, "data.zip")

    os.makedirs(extract_to, exist_ok=True)

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Unzipping data...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    os.remove(zip_path)
    print("Data downloaded and extracted.")

def load_documents(path: str) -> List[List[Document]]:
    print(f"Loading documents from {path}...")

    directories = [
        item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))
    ]

    document_lists = []
    for directory in directories:
        loader = DirectoryLoader(
            os.path.join(path, directory), glob="**/*.txt", loader_cls=TextLoader, show_progress=True
        )
        document_lists.append(loader.load())
    return document_lists

def prune_invalid_products(graph_documents):
    products = set()
    for graph_document in graph_documents:
        nodes_to_remove = []
        for node in graph_document.nodes:
            if node.type == "Product" and "features" not in node.properties:
                nodes_to_remove.append(node)
            elif node.type == "Product":
                products.add(node.id)
        for node in nodes_to_remove:
            graph_document.nodes.remove(node)
    return products

def prune_invalid_segments(graph_documents, valid_segments):
    for graph_document in graph_documents:
        nodes_to_remove = []
        for node in graph_document.nodes:
            if node.type == "Segment" and node.id not in valid_segments:
                nodes_to_remove.append(node)
        for node in nodes_to_remove:
            graph_document.nodes.remove(node)

def fix_directions(graph_documents, relation_name, wrong_source_type):
    for graph_document in graph_documents:
        for relationship in graph_document.relationships:
            if relationship.type == relation_name:
                if relationship.source.type == wrong_source_type:
                    source = relationship.source
                    target = relationship.target
                    relationship.source = target
                    relationship.target = source

def is_not_a_listed_product(node, products):
    if node.type == "Product" and node.id not in products:
        return True
    return False

def prune_dangling_relationships(graph_documents, products):
    for graph_document in graph_documents:
        relationships_to_remove = []
        for relationship in graph_document.relationships:
            if is_not_a_listed_product(relationship.source, products) or is_not_a_listed_product(
                relationship.target, products
            ):
                relationships_to_remove.append(relationship)
        for relationship in relationships_to_remove:
            graph_document.relationships.remove(relationship)

def prune_unwanted_relationships(graph_documents, relation_name, source_type, target_type):
    node_types = set([source_type, target_type])
    for graph_document in graph_documents:
        relationships_to_remove = []
        for relationship in graph_document.relationships:
            if (
                relationship.type == relation_name
                and set([relationship.source.type, relationship.target.type])
                == node_types
            ):
                relationships_to_remove.append(relationship)
        for relationship in relationships_to_remove:
            graph_document.relationships.remove(relationship)

def print_graph(graph_documents):
    for doc in graph_documents:
        print(f"{doc.source.page_content[:100]} === truncated ===")
        nodes = copy.deepcopy(doc.nodes)
        for node in nodes:
            if "embedding" in node.properties:
                node.properties["embedding"] = "..."
        print(nodes)
        print(doc.relationships)
        print()

def main():
    parser = argparse.ArgumentParser(description="Ingest retail data into BigQuery Graph.")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup existing graph data and exit (without ingesting).")
    parser.add_argument("--print-graph", action="store_true", help="Print the graph documents before ingestion.")
    parser.add_argument(
        "--llm_model",
        default="gemini-2.5-flash",
        help="Model name for ChatVertexAI (LLM). Default: gemini-2.5-flash",
    )
    parser.add_argument(
        "--embedding_model",
        default="gemini-embedding-001",
        help="Model name for VertexAIEmbeddings. Default: gemini-embedding-001",
    )
    parser.add_argument(
        "--project_id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="Google Cloud Project ID",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        help="BigQuery location. Default: us-central1",
    )
    parser.add_argument(
        "--dataset_id",
        default=os.environ.get("BIGQUERY_DATASET"),
        help="BigQuery Dataset ID",
    )
    parser.add_argument(
        "--graph_name",
        default=os.environ.get("BIGQUERY_GRAPH_NAME"),
        help="BigQuery Graph Name",
    )
    args = parser.parse_args()

    project_id = args.project_id
    location = args.location
    dataset_id = args.dataset_id
    graph_name = args.graph_name

    if not all([project_id, dataset_id, graph_name]):
        print("Error: Missing required configuration. Please set environment variables or provide command line arguments.")
        return

    print(f"Project: {project_id}")
    print(f"Location: {location}")
    print(f"Dataset: {dataset_id}")
    print(f"Graph: {graph_name}")

    # Create BigQuery dataset if it doesn't exist
    print("Ensuring BigQuery dataset exists...")
    bq_client = bigquery.Client(project=project_id)
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    try:
        bq_client.create_dataset(dataset)
        print(f"Dataset {project_id}:{dataset_id} created.")
    except Exception as e:
        print(f"Dataset already exists or error: {e}")

    # Initialize BigQueryGraphStore
    print("Initializing BigQueryGraphStore...")
    graph_store = BigQueryGraphStore(
        project_id=project_id,
        dataset_id=dataset_id,
        graph_name=graph_name,
        location=location,
    )

    if args.cleanup:
        print("Cleaning up existing graph data...")
        graph_store.cleanup()
        print("Cleanup complete. Exiting...")
        return

    # 1. Download and Extract Data
    data_url = "https://raw.githubusercontent.com/googleapis/langchain-google-spanner-python/main/samples/retaildata.zip"
    temp_dir = "temp_data"

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    download_and_unzip(data_url, temp_dir)

    # 2. Load Documents
    data_path = os.path.join(temp_dir, "retaildata")
    document_lists = load_documents(data_path)
    total_docs = sum(len(l) for l in document_lists)
    print(f"Loaded {len(document_lists)} directories containing {total_docs} documents.")

    # 3.a. Transform to Graph Documents
    print("Initializing LLMGraphTransformer...")
    llm = ChatVertexAI(model=args.llm_model, temperature=0)

    llm_transformer = LLMGraphTransformer(
        llm=llm,
        allowed_nodes=["Category", "Segment", "Tag", "Product", "Bundle", "Deal"],
        allowed_relationships=[
            "In_Category",
            "Tagged_With",
            "In_Segment",
            "In_Bundle",
            "Is_Accessory_Of",
            "Is_Upgrade_Of",
            "Has_Deal",
        ],
        node_properties=[
            "name",
            "price",
            "weight",
            "deal_end_date",
            "features",
        ],
    )

    print("Converting documents to graph documents (this may take a while)...")
    graph_documents = []
    for doc_list in document_lists:
        graph_documents.extend(llm_transformer.convert_to_graph_documents(doc_list))

    print(f"Converted to {len(graph_documents)} graph documents.")

    # 3.b. Post-process extracted nodes and edges
    print("Post-processing graph documents...")
    products = prune_invalid_products(graph_documents)
    prune_invalid_segments(graph_documents, set(["Home", "Office", "Fitness"]))
    prune_unwanted_relationships(graph_documents, "IN_CATEGORY", "Bundle", "Category")
    prune_unwanted_relationships(graph_documents, "IN_CATEGORY", "Deal", "Category")
    prune_unwanted_relationships(graph_documents, "IN_SEGMENT", "Bundle", "Segment")
    prune_unwanted_relationships(graph_documents, "IN_SEGMENT", "Deal", "Segment")
    prune_dangling_relationships(graph_documents, products)
    fix_directions(graph_documents, "HAS_DEAL", "Deal")
    fix_directions(graph_documents, "IN_BUNDLE", "Bundle")
    print("Post-processing complete.")

    if args.print_graph:
        print("Printing graph documents...")
        print_graph(graph_documents)

    # 4. Generate Embeddings for Product Nodes
    print("Generating embeddings for Product nodes...")
    embedding_service = VertexAIEmbeddings(model_name=args.embedding_model)

    for doc in tqdm.tqdm(graph_documents, desc="Embedding"):
        for node in doc.nodes:
            if node.type == "Product" and "features" in node.properties:
                 node.properties["embedding"] = embedding_service.embed_query(
                    node.properties["features"]
                )

    # 5. Ingest into BigQuery Graph
    print("Adding graph documents to BigQuery Graph...")
    graph_store.add_graph_documents(graph_documents)
    print("Ingestion complete.")

    # Cleanup temp data
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
