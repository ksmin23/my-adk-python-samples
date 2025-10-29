# Cloud Run과 Memorystore for Redis 연결 FAQ

이 문서는 Google Cloud Run 서비스에서 VPC 내부에 있는 Memorystore for Redis 인스턴스에 접속하는 방법에 대한 자주 묻는 질문과 답변을 정리합니다.

- [Q1: Cloud Run에서 Memorystore for Redis에 접속하려면 어떻게 해야 하나요?](#q1-cloud-run에서-memorystore-for-redis에-접속하려면-어떻게-해야-하나요)
- [Q2: Cloud Run의 네트워크는 어떻게 구성해야 Memorystore for Redis에 접속할 수 있나요?](#q2-cloud-run의-네트워크는-어떻게-구성해야-memorystore-for-redis에-접속할-수-있나요)
- [Q3: `gcloud` CLI를 사용하여 Memorystore for Redis (Valkey) 인스턴스를 생성하는 방법은 무엇인가요?](#q3-gcloud-cli를-사용하여-memorystore-for-redis-valkey-인스턴스를-생성하는-방법은-무엇인가요)
- [Q4: Q3의 명령어로 생성된 Memorystore for Redis는 Private Subnet에 설치되나요?](#q4-q3의-명령어로-생성된-memorystore-for-redis는-private-subnet에-설치되나요)
- [Q5: `gcloud` CLI로 Memorystore for Redis 인스턴스 정보를 확인하는 방법은 무엇인가요?](#q5-gcloud-cli로-memorystore-for-redis-인스턴스-정보를-확인하는-방법은-무엇인가요)
- [Q6: 확인된 Memorystore for Redis 정보를 이용해 Cloud Run 서비스를 어떻게 연결하나요?](#q6-확인된-memorystore-for-redis-정보를-이용해-cloud-run-서비스를-어떻게-연결하나요)
- [Q7: Cloud Run에서 Memorystore for Redis에 접속하기 위해 별도의 방화벽 규칙 설정이 필요한가요?](#q7-cloud-run에서-memorystore-for-redis에-접속하기-위해-별도의-방화벽-규칙-설정이-필요한가요)

---

### Q1: Cloud Run에서 Memorystore for Redis에 접속하려면 어떻게 해야 하나요?

**A:** Cloud Run은 서버리스 환경이고 Memorystore for Redis는 VPC 내부에 비공개 IP로 생성되므로 직접 통신할 수 없습니다. 이 둘을 연결하려면 **서버리스 VPC 액세스 커넥터(Serverless VPC Access Connector)** 를 사용해야 합니다.

전체 과정은 다음과 같습니다.

1.  **Memorystore for Redis 인스턴스 생성**: VPC 네트워크 내에 Redis 인스턴스를 준비합니다.
2.  **서버리스 VPC 액세스 커넥터 생성**: Redis와 동일한 VPC 네트워크에 커넥터를 생성합니다. 이 커넥터가 Cloud Run과 VPC를 연결하는 다리 역할을 합니다.
3.  **Cloud Run 서비스 배포**: Cloud Run 서비스를 배포하거나 업데이트할 때, 생성된 VPC 커넥터를 연결하도록 설정합니다.
4.  **애플리케이션 코드 수정**: 애플리케이션 코드에서 환경 변수 등을 통해 Redis의 비공개 IP 주소와 포트 정보를 받아 접속하도록 구현합니다.

---

### Q2: Cloud Run의 네트워크는 어떻게 구성해야 Memorystore for Redis에 접속할 수 있나요?

**A:** Cloud Run 서비스의 **아웃바운드(Egress) 트래픽** 설정을 VPC 네트워크로 향하도록 구성해야 합니다.

1.  **VPC 커넥터 연결**:
    - Cloud Run 서비스 설정의 '네트워킹' 탭에서 Memorystore가 있는 VPC에 미리 생성해 둔 **VPC 커넥터를 연결**합니다.
    - `gcloud` CLI에서는 `--vpc-connector` 플래그를 사용합니다.

2.  **VPC Egress (트래픽 라우팅) 설정 (권장)**:
    - **'비공개 IP로 전송되는 요청만 VPC 커넥터로 라우팅'** (`private-ranges-only`) 옵션을 선택합니다.
    - 이 설정은 Memorystore와 같은 내부 IP로 향하는 트래픽만 VPC 커넥터로 보내고, 외부 인터넷으로 향하는 트래픽은 직접 내보내므로 가장 효율적입니다.
    - `gcloud` CLI에서는 `--vpc-egress=private-ranges-only` 플래그를 사용합니다.

**gcloud 명령어 예시:**
```bash
gcloud run deploy [SERVICE_NAME] \
  --image=[IMAGE_URL] \
  --region=[REGION] \
  --vpc-connector=[CONNECTOR_NAME] \
  --vpc-egress=private-ranges-only \
  --set-env-vars REDIS_HOST=[REDIS_IP_ADDRESS],REDIS_PORT=[REDIS_PORT]
```

---

### Q3: `gcloud` CLI를 사용하여 Memorystore for Redis (Valkey) 인스턴스를 생성하는 방법은 무엇인가요?

**A:** 아래 `gcloud` 명령어를 사용하여 기본적인 Memorystore for Redis 인스턴스를 생성할 수 있습니다.

```bash
gcloud redis instances create my-redis-instance \
    --size=1 \
    --region=us-central1 \
    --tier=BASIC \
    --redis-version=REDIS_7_2 \
    --network=default
```

- **`my-redis-instance`**: 생성할 인스턴스의 이름
- **`--size`**: 메모리 크기 (GB)
- **`--region`**: 인스턴스를 생성할 GCP 리전
- **`--tier`**: `BASIC` (독립형) 또는 `STANDARD_HA` (고가용성)
- **`--redis-version`**: Redis 버전
- **`--network`**: 연결할 VPC 네트워크 (기본: `default`)

---

### Q4: [Q3의 명령어](#q3-gcloud-cli를-사용하여-memorystore-for-redis-valkey-인스턴스를-생성하는-방법은-무엇인가요)로 생성된 Memorystore for Redis는 Private Subnet에 설치되나요?

**A:** 네, 맞습니다. Memorystore for Redis는 항상 VPC 네트워크 내부에 **비공개(Private) IP 주소**를 할당받아 생성됩니다. 외부 인터넷에 직접 노출되지 않으므로 안전한 Private Subnet에 설치되는 것과 동일한 효과를 가집니다. 같은 VPC 네트워크에 속한 리소스들만 내부 IP를 통해 이 인스턴스에 접근할 수 있습니다.

---

### Q5: `gcloud` CLI로 Memorystore for Redis 인스턴스 정보를 확인하는 방법은 무엇인가요?

**A:** `gcloud redis instances describe` 명령어를 사용하여 특정 인스턴스의 상세 정보를 확인할 수 있습니다.

**특정 인스턴스 정보 확인:**
```bash
# [INSTANCE_NAME]과 [REGION]을 실제 값으로 변경하세요.
gcloud redis instances describe [INSTANCE_NAME] --region=[REGION]
```
이 명령어를 실행하면 인스턴스의 IP 주소(`host`), 포트(`port`), VPC 네트워크(`authorizedNetwork`) 등 연결에 필요한 모든 정보를 얻을 수 있습니다.

**프로젝트 내 모든 인스턴스 목록 확인:**
```bash
# 특정 리전의 모든 인스턴스를 보려면 --region 플래그를 사용하세요.
gcloud redis instances list --region=[REGION]
```

---

### Q6: [확인된 Memorystore for Redis 정보](#q5-gcloud-cli로-memorystore-for-redis-인스턴스-정보를-확인하는-방법은-무엇인가요)를 이용해 Cloud Run 서비스를 어떻게 연결하나요?

**A:** 3단계 과정을 통해 연결할 수 있습니다. Redis는 비공개 IP를 사용하므로 Cloud Run이 VPC 네트워크에 접근할 수 있도록 설정하는 것이 핵심입니다.

**1단계: Serverless VPC Access 커넥터 생성**
Cloud Run과 Redis가 있는 VPC 네트워크를 연결할 커넥터를 생성합니다. (이미 있다면 이 단계는 생략)
```bash
gcloud compute networks vpc-access connectors create redis-connector \
  --network default \
  --region us-central1 \
  --range "10.8.0.0/28"
```
*   `--network`와 `--region`은 Redis 인스턴스와 동일한 값으로 설정해야 합니다.

**2단계: VPC 커넥터와 환경 변수를 설정하여 Cloud Run 배포**
`gcloud run deploy` 명령어를 사용하여 VPC 커넥터를 연결하고, Redis 접속 정보를 환경 변수로 주입합니다.
```bash
gcloud run deploy [SERVICE_NAME] \
  --image [IMAGE_NAME] \
  --region us-central1 \
  --vpc-connector redis-connector \
  --vpc-egress all-traffic \
  --set-env-vars REDIS_HOST=[REDIS_IP_ADDRESS],REDIS_PORT=[REDIS_PORT]
```
*   `--vpc-egress all-traffic`: Cloud Run에서 나가는 모든 트래픽이 VPC를 통하도록 설정하여 Redis의 비공개 IP에 접근할 수 있게 합니다.
*   `REDIS_HOST`와 `REDIS_PORT`에는 **Q5**에서 확인한 `host`와 `port` 값을 입력합니다.

**3단계: 애플리케이션 코드에서 환경 변수 사용**
코드 내에서 환경 변수(`REDIS_HOST`, `REDIS_PORT`)를 읽어 Redis 클라이언트를 초기화합니다.

```python
# Python 예시
import os
import redis

redis_host = os.environ.get('REDIS_HOST')
redis_port = int(os.environ.get('REDIS_PORT'))

redis_client = redis.Redis(host=redis_host, port=redis_port)
```

---

### Q7: Cloud Run에서 Memorystore for Redis에 접속하기 위해 별도의 방화벽 규칙 설정이 필요한가요?

**A:** 아니요, 일반적으로 **추가 방화벽 설정은 필요하지 않습니다.**

Google Cloud의 `default` VPC 네트워크에는 `default-allow-internal`이라는 기본 방화벽 규칙이 있어, VPC 내부의 모든 리소스 간 통신을 허용합니다. Cloud Run은 VPC 커넥터를 통해 VPC 내부의 구성 요소처럼 동작하므로, 이 규칙에 따라 별도 설정 없이 Redis 인스턴스와 통신할 수 있습니다.

단, `default-allow-internal` 규칙을 직접 수정했거나, 내부 통신 규칙이 없는 커스텀 VPC를 사용하는 경우에는 방화벽 규칙을 직접 설정해야 할 수 있습니다.
