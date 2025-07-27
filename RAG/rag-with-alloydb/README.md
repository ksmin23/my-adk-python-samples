# AlloyDB Vector Search를 이용한 Agentic RAG 프로젝트

이 프로젝트는 ADK (Agent Development Kit)와 AlloyDB for PostgreSQL의 Vector Search 기능을 사용하여 Agentic RAG를 구현한 샘플입니다.

## 프로젝트 구조

```
/rag_with_alloydb_project
├── rag_with_alloydb/          # ADK Agent 디렉터리
│   └── requirements.txt     # 에이전트 의존성
├── data_ingestion/          # 데이터 수집 디렉터리
│   └── requirements.txt     # 데이터 수집 스크립트 의존성
├── source_documents/        # RAG의 기반이 될 원본 문서
└── README.md
```

## 설정 방법

### 1. 의존성 설치

이 프로젝트는 `uv`를 사용하여 파이썬 가상 환경 및 패키지 의존성을 관리합니다.

**가상 환경 생성 및 활성화:**
```bash
# 가상 환경 생성
uv venv

# 가상 환경 활성화 (macOS/Linux)
source .venv/bin/activate
# 가상 환경 활성화 (Windows)
.venv\Scripts\activate
```

**의존성 설치:**
```bash
# 에이전트 의존성 설치
uv pip install -r rag_with_alloydb/requirements.txt

# Data Ingestion 스크립트 의존성 설치
uv pip install -r data_ingestion/requirements.txt
```

### 2. 데이터 수집 (Data Ingestion)

`data_ingestion/ingest.py` 스크립트를 실행하여 `source_documents`에 있는 문서들을 AlloyDB에 적재합니다.

먼저, `data_ingestion/.env.example` 파일을 복사하여 `data_ingestion/.env` 파일을 생성하고, 필요한 값들을 채워넣어야 합니다.

```bash
cp data_ingestion/.env.example data_ingestion/.env
# 이제 data_ingestion/.env 파일을 에디터로 열어 값을 수정하세요.
```

`.env` 파일이 준비되면, 다음 명령어로 데이터 수집 스크립트를 실행할 수 있습니다. 명령줄 인자를 사용하여 `.env` 파일의 값을 덮어쓸 수도 있습니다.

**실행 예시:**
```bash
python data_ingestion/ingest.py \
  --database="your-alloydb-database" \
  --table_name="vector_store" \
  --user="your-db-user" \
  --password="your-db-password" \
  --source_dir="source_documents/"
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


