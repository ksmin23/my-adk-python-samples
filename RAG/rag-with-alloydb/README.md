# AlloyDB Vector Search를 이용한 Agentic RAG 프로젝트

이 프로젝트는 ADK (Agent Development Kit)와 AlloyDB for PostgreSQL의 Vector Search 기능을 사용하여 Agentic RAG를 구현한 샘플입니다.

## 프로젝트 구조

```
/rag_with_alloydb_project
├── rag_with_alloydb/          # ADK Agent 디렉터리
├── data_ingestion/          # 데이터 수집 디렉터리
├── source_documents/        # RAG의 기반이 될 원본 문서
├── requirements.txt         # 프로젝트 전체 의존성
└── README.md
```

## 설정 방법

### 1. 의존성 설치

**공통 의존성:**
```bash
pip install -r requirements.txt
```

**Data Ingestion 스크립트 의존성:**
```bash
pip install -r data_ingestion/requirements.txt
```

### 2. 데이터 수집 (Data Ingestion)

`data_ingestion/ingest.py` 스크립트를 실행하여 `source_documents`에 있는 문서들을 AlloyDB에 적재합니다.

**실행 예시:**
```bash
python data_ingestion/ingest.py \
  --project_id="your-gcp-project-id" \
  --region="your-alloydb-region" \
  --cluster="your-alloydb-cluster" \
  --instance="your-alloydb-instance" \
  --database="your-alloydb-database" \
  --user="your-db-user" \
  --password="your-db-password"
```

### 3. 에이전트 실행

ADK CLI를 사용하여 에이전트를 실행합니다.

```bash
adk run rag_with_alloydb
```

## Reference

### Official Google Cloud Docs
- [Perform a vector search | AlloyDB for PostgreSQL | Google Cloud](https://cloud.google.com/alloydb/docs/ai/perform-vector-search)
- [Run a vector similarity search | AlloyDB for PostgreSQL | Google ...](https://cloud.google.com/alloydb/docs/ai/run-vector-similarity-search)
- [Generate text embeddings](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings?resource=google_ml)

### Google Codelabs
- [Getting started with Vector Embeddings with AlloyDB AI](https://codelabs.developers.google.com/alloydb-ai-embedding#0)
- [Build a Patent Search App with AlloyDB, Vector Search & Vertex AI!](https://codelabs.developers.google.com/patent-search-alloydb-gemini#0)
- [Building a Smart Shop Agent with Gemini and AlloyDB Omni | Codelabs | Google for Developers](https://codelabs.developers.google.com/smart-shop-agent-alloydb#0)

### LangChain Integration
- [Google AlloyDB for PostgreSQL | 🦜️ LangChain](https://python.langchain.com/docs/integrations/vectorstores/google_alloydb/)


