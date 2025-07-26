## AlloyDB Vector Search를 활용한 Agentic RAG 개발 PRD

---

**문서 제목:** AlloyDB 기반 Agentic RAG 에이전트 개발
**작성자:** Gemini
**작성일:** 2025년 7월 25일
**버전:** 1.0

### 1. 개요 (Overview)

본 문서는 Google Cloud의 **AlloyDB for PostgreSQL**이 제공하는 Vector Search 기능을 활용하여, 특정 지식 베이스에 기반한 질문에 정확하고 신뢰도 높은 답변을 생성하는 **Agentic RAG (Retrieval-Augmented Generation)** 에이전트 개발을 위한 요구사항을 정의합니다.

본 프로젝트의 에이전트는 **ADK (Agent Development Kit)** 프레임워크를 사용하여 개발되며, 핵심 LLM으로는 **Gemini 1.5 Flash** 모델을 사용합니다. 에이전트의 이름은 `rag_with_alloydb`로 지정합니다.

데이터베이스에 지식 데이터를 저장하고 벡터 임베딩을 생성하는 **데이터 수집(Data Ingestion) 파이프라인**은 에이전트 로직과 물리적으로 분리된 디렉터리에서 독립적으로 관리하여 모듈성을 확보합니다.

### 2. 목표 (Goals and Objectives)

*   **주요 목표:** 사용자의 질문 의도를 파악하여, AlloyDB에 저장된 내부 지식 베이스를 동적으로 검색하고, 검색된 정보를 근거로 신뢰성 있는 답변을 생성하는 `rag_with_alloydb` 에이전트를 개발합니다.
*   **세부 목표:**
    1.  ADK 프레임워크를 사용하여 `rag_with_alloydb` 에이전트의 기본 구조를 구현합니다.
    2.  사용자 질문을 벡터로 변환하고 AlloyDB의 Vector Search를 통해 관련성 높은 문서를 효율적으로 검색하는 RAG 파이프라인을 구축합니다.
    3.  검색된 컨텍스트와 사용자 질문을 조합하여 `gemini-1.5-flash` 모델에 전달하고, 최종 답변을 생성하는 로직을 구현합니다.
    4.  문서(txt, md 등)를 읽어와 청크(Chunk)로 분할하고, 벡터 임베딩을 생성하여 AlloyDB에 저장하는 데이터 수집 스크립트를 별도의 디렉터리에 개발합니다.

### 3. 기능 요구사항 (Functional Requirements)

#### 3.1. `rag_with_alloydb` 에이전트
*   **입력:** 사용자로부터 자연어 질문을 입력받습니다.
*   **처리:**
    1.  **질문 분석:** 에이전트는 입력된 질문이 외부 지식(DB 정보)을 필요로 하는지 판단합니다.
    2.  **임베딩 생성:** 질문을 벡터 임베딩으로 변환합니다. (예: `text-embedding-004` 모델 사용)
    3.  **벡터 검색:** 생성된 임베딩을 사용하여 AlloyDB에 저장된 문서 벡터들과 유사도 검색(Similarity Search)을 수행하고, 관련성이 가장 높은 상위 K개의 문서 청크를 검색합니다.
    4.  **프롬프트 구성:** 원본 질문과 검색된 문서 청크(컨텍스트)를 결합하여 `gemini-1.5-flash` 모델에 전달할 프롬프트를 동적으로 구성합니다.
    5.  **답변 생성:** 구성된 프롬프트를 LLM에 전달하여 최종 답변을 생성합니다.
*   **출력:** 검색된 정보를 바탕으로 생성된 자연어 답변을 사용자에게 반환합니다.

#### 3.2. 데이터 수집 (Data Ingestion)
*   독립된 `data_ingestion` 디렉터리 내에서 스크립트로 실행되어야 합니다.
*   **입력:** 지정된 디렉터리에 있는 소스 문서 파일(예: `.txt`, `.md`).
*   **처리:**
    1.  **문서 로드 및 분할:** 문서를 로드하여 의미 있는 단위의 청크로 분할합니다.
    2.  **임베딩 생성:** 각 문서 청크에 대한 벡터 임베딩을 생성합니다.
    3.  **데이터 저장:** 원본 텍스트 청크와 해당 벡터 임베딩을 AlloyDB의 지정된 테이블에 저장합니다.
*   **출력:** AlloyDB 테이블에 지식 데이터가 적재됩니다.

#### 3.3. AlloyDB 연동
*   **테이블 구조:** 최소한 `id`, `content` (텍스트 청크), `embedding` (벡터) 컬럼을 포함해야 합니다.
*   **인덱싱:** `embedding` 컬럼에는 벡터 검색 성능 최적화를 위해 HNSW(Hierarchical Navigable Small World) 인덱스가 적용되어야 합니다.
*   **보안:** 데이터베이스 연결 정보(자격 증명)는 코드에 하드코딩되지 않고 환경 변수나 보안 관리 도구를 통해 안전하게 관리되어야 합니다.

### 4. 비기능 요구사항 (Non-Functional Requirements)

*   **성능 (Performance):** 사용자 질문에 대한 답변 생성까지의 총 소요 시간(End-to-end latency)은 실시간 상호작용이 가능한 수준(예: 5초 이내)을 목표로 합니다.
*   **모듈성 (Modularity):** 에이전트 로직과 데이터 수집 로직은 명확히 분리되어야 하며, 서로에게 미치는 영향을 최소화해야 합니다.
*   **확장성 (Scalability):** AlloyDB에 저장되는 문서의 수가 증가하더라도 검색 성능이 선형적으로 저하되지 않아야 합니다.
*   **보안 (Security):** 모든 클라우드 서비스(AlloyDB, Vertex AI)와의 통신은 암호화되어야 하며, IAM 역할을 통해 최소 권한 원칙을 준수해야 합니다.

### 5. 기술 스택 및 아키텍처 (Tech Stack & Architecture)

*   **프로그래밍 언어:** Python
*   **에이전트 프레임워크:** ADK (Agent Development Kit)
*   **LLM:** Google Gemini 1.5 Flash
*   **Embedding Model:** Google `text-embedding-004` (또는 동급 모델)
*   **Vector Database:** Google Cloud AlloyDB for PostgreSQL (with `google_ml_integration` extension)
*   **제안 디렉터리 구조:**
    ```
    /rag_with_alloydb_project
    ├── rag_with_alloydb/          # ADK Agent 디렉터리
    │   ├── __init__.py
    │   ├── agent.py             # 에이전트 핵심 로직
    │   ├── alloydb_connector.py # AlloyDB 연결 및 검색 모듈
    │   └── ...
    ├── data_ingestion/          # 데이터 수집 디렉터리
    │   ├── __init__.py
    │   ├── ingest.py            # 데이터 수집 및 임베딩 생성 스크립트
    │   └── requirements.txt
    ├── source_documents/        # RAG의 기반이 될 원본 문서
    │   ├── doc1.txt
    │   └── doc2.md
    ├── requirements.txt         # 프로젝트 전체 의존성
    └── README.md
    ```

### 6. 제외 범위 (Out of Scope)

*   사용자와 상호작용하는 UI(웹, 앱 등) 개발. 본 프로젝트는 백엔드 에이전트 개발에 집중합니다.
*   실시간 데이터 동기화. 데이터 수집은 배치(Batch) 작업으로 수행하는 것을 기본으로 합니다.
*   복잡한 데이터 정제 및 전처리 파이프라인 구축.
*   AlloyDB 검색 외 다른 도구를 사용하는 복합적인 에이전트 기능(Multi-tool Agent).
