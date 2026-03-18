import os
import argparse
import time
import logging
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: file_search_stores is currently exclusive to the Gemini Developer API.
# Initializing with vertexai=True will cause store management to fail.
genai_client = genai.Client()

def get_store(display_name: str):
    """Retrieve a store by its display name"""
    try:
        for a_store in genai_client.file_search_stores.list():
            if a_store.display_name == display_name:
                return a_store
    except Exception as e:
        logger.error(f"Error retrieving store '{display_name}': {e}")
    return None

def create_store(display_name: str):
    """Create a new File Search Store if it doesn't exist"""
    store = get_store(display_name)
    if store:
        logger.info(f"Store '{display_name}' already exists: {store.name}")
        return store

    logger.info(f"Creating store '{display_name}'...")
    store = genai_client.file_search_stores.create(config={"display_name": display_name})
    logger.info(f"Successfully created store: {store.name}")
    return store

def delete_store(display_name: str):
    """Delete a store by its display name"""
    store = get_store(display_name)
    if not store:
        logger.warning(f"Store '{display_name}' not found. Nothing to delete.")
        return

    logger.info(f"Deleting store '{display_name}' ({store.name})...")
    genai_client.file_search_stores.delete(name=store.name)
    logger.info("Successfully deleted store.")

def list_documents(display_name: str):
    """List all documents in a store"""
    store = get_store(display_name)
    if not store:
        logger.error(f"Store '{display_name}' not found.")
        return []

    docs = genai_client.file_search_stores.documents.list(parent=store.name)
    try:
        doc_list = list(docs)
        print(f"Docs in {display_name}: {len(doc_list)}")

        if not doc_list:
            print("No documents found in the store.")
        else:
            for i, doc in enumerate(doc_list):
                section_heading = f"Document {i}:"
                print("-" * len(section_heading))
                print(section_heading)
                print("-" * len(section_heading))
                print(f"  Display name: {doc.display_name}")
                print(f"  ID: {doc.name}")
                print(f"  Metadata: {doc.custom_metadata}")
        return doc_list
    except Exception as e:
        print(f"Error listing docs (might be empty): {e}")
        return []

def delete_document(target: str, store_display_name: str):
    """Delete a document by its doc_id (resource name) or filename/display_name"""
    # If it looks like a resource name, delete it directly
    if target.startswith("fileSearchStores/"):
        logger.info(f"Deleting document by ID: {target}")
        genai_client.file_search_stores.documents.delete(name=target, config={"force": True})
        return

    store = get_store(store_display_name)
    if not store:
        logger.error(f"Store '{store_display_name}' not found. Cannot search for document to delete.")
        return
        
    for doc in genai_client.file_search_stores.documents.list(parent=store.name):
        should_delete = False
        if doc.display_name == target:
            should_delete = True
        elif doc.custom_metadata:
            for meta in doc.custom_metadata:
                if meta.key == "filename" and meta.string_value == target:
                    should_delete = True
                    break
        
        if should_delete:
            logger.info(f"Deleting document: '{doc.display_name}' (ID: {doc.name})")
            genai_client.file_search_stores.documents.delete(name=doc.name, config={"force": True})
            time.sleep(1)

def upload_document(file_path: str, store_display_name: str, metadata_str: Optional[str] = None, delete_existing: bool = True):
    """Upload a document to the store with metadata"""
    store = get_store(store_display_name)
    if not store:
        logger.error(f"Store '{store_display_name}' not found. Cannot upload.")
        return

    filename = os.path.basename(file_path)

    # Check for existing and delete
    if delete_existing:
        delete_document(filename, store_display_name)

    # Prepare custom metadata
    custom_metadata = [{"key": "filename", "string_value": filename}]
    display_name = filename

    if metadata_str:
        pairs = metadata_str.split(",")
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                key, value = k.strip(), v.strip()
                custom_metadata.append({"key": key, "string_value": value})

    # Upload to File Search Store
    logger.info(f"Indexing '{filename}' into store '{store_display_name}'...")

    operation = genai_client.file_search_stores.upload_to_file_search_store(
        file_search_store_name=store.name,
        file=file_path,
        config={
            "display_name": display_name,
            "custom_metadata": custom_metadata,
        },
    )

    start_time = time.time()
    timeout = 180  # 3 minutes timeout

    try:
        while not operation.done:
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached ({timeout}s). The indexing might still be running in the background.")
                break

            time.sleep(2)
            operation = genai_client.operations.get(operation)
            
            if operation.error:
                logger.error(f"Indexing failed: {operation.error}")
                return

        if operation.done:
            logger.info(f"Successfully indexed '{filename}' as '{display_name}'")
        else:
            logger.info(f"Indexing operation ID: {operation.name}")

    except KeyboardInterrupt:
        logger.info("\nPolling interrupted by user. The operation may still be processing on the server.")
        return

def query_store(query: str, store_display_name: str, model_name: str, metadata_filter: Optional[str] = None):
    """Perform a RAG query against the store"""
    store = get_store(store_display_name)
    if not store:
        logger.error("Store not found.")
        return

    logger.info(f"Querying store '{store_display_name}' for: '{query}'...")
    if metadata_filter:
        logger.info(f"Using metadata filter: {metadata_filter}")

    response = genai_client.models.generate_content(
        model=model_name,
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(file_search=types.FileSearch(
                file_search_store_names=[store.name],
                metadata_filter=metadata_filter
            ))]
        ),
    )
    return response.text

def main():
    DEFAULT_MODEL = os.getenv("MODEL", "gemini-2.5-flash")
    DEFAULT_STORE_NAME = os.getenv("STORE_NAME")

    parser = argparse.ArgumentParser(description="Gemini File Search Store Utilities")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Gemini model to use (default: {DEFAULT_MODEL})")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List
    list_parser = subparsers.add_parser("list", help="List all documents in a store")
    list_parser.add_argument("--store", "-s", default=DEFAULT_STORE_NAME, help="Display name of the store (default: from .env)")

    # Create
    create_parser = subparsers.add_parser("create", help="Create a new store")
    create_parser.add_argument("--store", "-s", required=True, help="Display name for the new store")

    # Delete Store
    delete_store_parser = subparsers.add_parser("delete-store", help="Delete a store")
    delete_store_parser.add_argument("--store", "-s", required=True, help="Display name of the store to delete")

    # Upload
    upload_parser = subparsers.add_parser("upload", help="Upload a document to the store")
    upload_parser.add_argument("--path", "-p", required=True, help="Path to the file to upload")
    upload_parser.add_argument("--store", "-s", default=DEFAULT_STORE_NAME, help="Display name of the store (default: from .env)")
    upload_parser.add_argument("--metadata", "-m", help="Metadata as key=value pairs, comma-separated (e.g., 'title=My Doc,author=Me')")
    upload_parser.add_argument("--no-delete", action="store_false", dest="delete_existing", help="Do not delete existing documents with the same filename")
    upload_parser.set_defaults(delete_existing=True)

    # Delete Document
    delete_doc_parser = subparsers.add_parser("delete-doc", help="Delete a document by filename or doc_id")
    delete_doc_parser.add_argument("--target", "-t", required=True, help="Filename, display name, or full doc_id (e.g., 'fileSearchStores/<store_name>/documents/<doc_id>')")
    delete_doc_parser.add_argument("--store", "-s", default=DEFAULT_STORE_NAME, help="Display name of the store (default: from .env, required if target is filename)")

    # Query
    query_parser = subparsers.add_parser("query", help="Query the store (RAG)")
    query_parser.add_argument("--query", "-q", required=True, help="The question to ask")
    query_parser.add_argument("--store", "-s", default=DEFAULT_STORE_NAME, help="Display name of the store (default: from .env)")
    query_parser.add_argument("--filter", "-f", help="Metadata filter string (e.g., 'user_id=\"user123\" and session_id=\"1234\"')")

    args = parser.parse_args()

    if args.command == "list":
        if not args.store:
            print("Error: store name is required (either as --store or in .env STORE_NAME)")
            return
        list_documents(args.store)
    elif args.command == "create":
        create_store(args.store)
    elif args.command == "delete-store":
        delete_store(args.store)
    elif args.command == "upload":
        if not args.store:
            print("Error: store name is required (either as --store or in .env STORE_NAME)")
            return
        upload_document(args.path, args.store, args.metadata, args.delete_existing)
    elif args.command == "delete-doc":
        delete_document(args.target, args.store)
    elif args.command == "query":
        if not args.store:
            print("Error: store name is required (either as --store or in .env STORE_NAME)")
            return
        answer = query_store(args.query, args.store, args.model, args.filter)
        print(f"\nAnswer:\n{answer}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
