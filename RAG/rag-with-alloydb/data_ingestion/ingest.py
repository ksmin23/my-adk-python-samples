
import argparse
import os
import time

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores.alloydb import AlloyDBEngine, AlloyDBVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 환경 변수 설정
os.environ["GOOGLE_CLOUD_PROJECT"] = "gcp-project-id"

def main(
    project_id: str,
    region: str,
    cluster: str,
    instance: str,
    database: str,
    user: str,
    password: str,
    table_name: str = "documents",
):
    """
    문서를 로드하고, 분할하고, 임베딩하여 AlloyDB에 저장합니다.
    """
    # 1. 문서 로드
    print("Loading documents...")
    loader = DirectoryLoader("../source_documents/", glob="**/*.md")
    docs = loader.load()
    print(f"Loaded {len(docs)} documents.")

    # 2. 문서 분할
    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    print(f"Split into {len(splits)} chunks.")

    # 3. AlloyDB 엔진 초기화
    print("Initializing AlloyDB engine...")
    engine = AlloyDBEngine.from_instance(
        project_id=project_id,
        region=region,
        cluster=cluster,
        instance=instance,
        database=database,
        user=user,
        password=password,
    )

    # 4. 임베딩 모델 초기화
    print("Initializing VertexAIEmbeddings...")
    embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@latest")

    # 5. AlloyDB VectorStore 초기화 및 데이터 저장
    print(f"Initializing AlloyDBVectorStore and adding documents to table '{table_name}'...")
    vector_store = AlloyDBVectorStore.create_sync(
        engine=engine,
        table_name=table_name,
        embedding_service=embeddings,
        documents=splits,
    )
    print("Data ingestion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into AlloyDB.")
    parser.add_argument("--project_id", required=True, help="Google Cloud project ID.")
    parser.add_argument("--region", required=True, help="AlloyDB region.")
    parser.add_argument("--cluster", required=True, help="AlloyDB cluster name.")
    parser.add_argument("--instance", required=True, help="AlloyDB instance name.")
    parser.add_argument("--database", required=True, help="AlloyDB database name.")
    parser.add_argument("--user", required=True, help="AlloyDB database user.")
    parser.add_argument("--password", required=True, help="AlloyDB database password.")
    parser.add_argument(
        "--table_name", default="documents", help="Table name for storing vectors."
    )
    args = parser.parse_args()

    main(
        project_id=args.project_id,
        region=args.region,
        cluster=args.cluster,
        instance=args.instance,
        database=args.database,
        user=args.user,
        password=args.password,
        table_name=args.table_name,
    )
