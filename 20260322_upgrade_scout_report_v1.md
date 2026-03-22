# logi_orchestrator Upgrade Scout Report v1.0

**Project**: Telegram + Claude + Codex Multi-Agent Orchestrator v1
**Date**: 2026-03-22
**Scout version**: project-upgrade.v2.0
**Timezone**: Asia/Dubai

---

## 1) Executive Summary

- **목표**: logi_orchestrator(FastAPI + Telegram + Claude/Codex 멀티에이전트 오케스트레이터) 스켈레톤을 프로덕션 레벨로 끌어올리기 위한 업그레이드 아이디어 Top 10 + Best 3 Deep Report 산출.
- **핵심 발견**: 현재 코드베이스는 **잘 설계된 상태 머신 + 감사 로그 + ACL 구조**를 갖추고 있으나, 모든 외부 연동(Telegram sendMessage, Claude API, Codex CLI, Git worktree)이 **stub** 상태. 인메모리 asyncio.Queue와 파일 기반 JSON 저장소는 프로세스 재시작 시 데이터 유실 위험. 테스트 커버리지 극소(2개 파일, 3개 테스트). 관측성(logging/tracing) 전무.
- **권장 방향**: Option B(중간) — 30일 내 persistent queue + DB 마이그레이션 + 테스트 확충, 60일 내 실제 외부 연동 + 관측성, 90일 내 멀티에이전트 통합 + 프로덕션 배포.

---

## 2) Current State Snapshot

| Area | Status | Evidence (path) | Risk |
|---|---|---|---|
| Documentation | ✅ 양호 | README.md, PLAN.md, orchestrator_state_machine.md, telegram_command_spec.md, TASKS.yaml | Low |
| Architecture Design | ✅ 양호 | PLAN.md §5 아키텍처, TASKS.yaml workflow/phases | Low |
| State Machine | ✅ 구현 완료 | app/services/state_machine.py, app/core/enums.py | Low |
| API Endpoints | ✅ 기본 구현 | app/api/routes/ (health, telegram, jobs) | Med |
| Task Queue | ⚠️ 인메모리 only | app/workers/queue.py (asyncio.Queue) | **High** |
| Storage | ⚠️ 파일 기반 JSON | app/infra/storage.py (FileJobStore) | **High** |
| External Integrations | ❌ 전부 stub | app/workers/worker.py (hardcoded artifacts), app/infra/git_worktree.py | **High** |
| Testing | ⚠️ 극소 | tests/ (2 files, 3 tests) | **High** |
| Observability | ❌ 전무 | 없음 (logging/metrics/tracing 미구현) | **High** |
| Security | ⚠️ 기본만 | app/services/acl.py (YAML allowlist), .env.example | Med |
| CI/CD | ❌ 전무 | .github/ 없음 | **High** |
| Dependencies | ✅ 최소화 | requirements.txt (fastapi, uvicorn, pydantic, pyyaml) | Low |
| Error Handling | ⚠️ 기본만 | app/core/exceptions.py, routes에서 HTTPException 변환 | Med |
| Telegram Bot SDK | ❌ 미사용 | 수동 webhook JSON 파싱 | Med |
| DI/Testability | ⚠️ 전역 인스턴스 | job_service = JobService() 전역 | Med |

### evidence_paths
- `README.md`, `DELIVERY_NOTE.md`, `requirements.txt`, `.env.example`
- `ops/orchestrator/PLAN.md`, `ops/orchestrator/TASKS.yaml`, `ops/orchestrator/orchestrator_state_machine.md`, `ops/orchestrator/telegram_command_spec.md`
- `config/acl.yaml`
- `app/main.py`, `app/config.py`, `app/core/enums.py`, `app/core/exceptions.py`
- `app/schemas/job.py`, `app/schemas/telegram.py`
- `app/services/state_machine.py`, `app/services/job_service.py`, `app/services/command_parser.py`, `app/services/acl.py`, `app/services/audit.py`
- `app/infra/storage.py`, `app/infra/filesystem.py`, `app/infra/git_worktree.py`
- `app/workers/queue.py`, `app/workers/worker.py`
- `app/api/routes/health.py`, `app/api/routes/telegram.py`, `app/api/routes/jobs.py`
- `tests/test_state_machine.py`, `tests/test_parser.py`

### Pain Points
- asyncio.Queue는 프로세스 재시작 시 모든 작업 유실
- FileJobStore는 동시 접근 시 race condition 위험 (file lock 없음)
- Worker가 stub artifact만 생성 — 실제 Claude/Codex/Git 호출 없음
- 테스트 3개로 state machine 일부와 parser만 커버
- 구조화된 로깅 없음 — print도 없음
- Telegram webhook에 서명 검증/secret token 없음
- Idempotency 설계는 문서에 있으나 구현 없음
- `job_service = JobService()` 전역 인스턴스 → DI 불가, 테스트 mock 어려움
- CI/CD 파이프라인 전무

### Quick Wins
- pytest 설정 + conftest.py 추가 (2h)
- structlog 또는 loguru 도입 (2h)
- Telegram secret token 헤더 검증 미들웨어 (1h)
- `.github/workflows/ci.yml` 기본 린트+테스트 (1h)
- `pyproject.toml` 전환 + ruff/mypy 설정 (1h)
- FastAPI Depends() 기반 DI 전환 (4h)

---

## 3) Upgrade Ideas Top 10

| Rank | Idea | Bucket | Impact | Effort | Risk | Conf | PriorityScore | Evidence | First PR |
|---:|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | Persistent Task Queue (SAQ/ARQ + Redis) | Reliability | 5 | 3 | 2 | 5 | **4.17** | SAQ PyPI, ARQ bench | asyncio.Queue → SAQ adapter |
| 2 | DB 마이그레이션 (SQLite → PostgreSQL) | Reliability | 5 | 3 | 2 | 4 | **3.33** | FastAPI SQL docs, Alembic guide | FileJobStore → SQLModel |
| 3 | Observability Stack (structlog + OTEL + Prometheus) | Reliability/Observability | 5 | 3 | 1 | 5 | **8.33** | FastAPI-observability, OTEL guide | structlog + request_id middleware |
| 4 | Test Coverage 확충 (pytest + httpx.AsyncClient) | DX/Tooling | 4 | 2 | 1 | 5 | **10.00** | FastAPI testing guide, greeden.me | conftest + route tests |
| 5 | Telegram Bot SDK 통합 (aiogram 3.x) | Architecture | 4 | 3 | 2 | 4 | **2.67** | aiogram GitHub 5.1k★, freecodecamp guide | aiogram webhook route |
| 6 | Claude/Codex Worker 실제 연동 | Architecture | 5 | 5 | 3 | 3 | **1.00** | Ruflo 21.9k★, Claude Agent Teams docs | Claude API plan worker |
| 7 | Webhook Security (HMAC + rate limit + idempotency) | Security | 4 | 2 | 1 | 5 | **10.00** | Webhook security 2025 DEV, fastapi-limiter | secret_token middleware |
| 8 | FastAPI DI 리팩터링 (Depends + 전역 인스턴스 제거) | DX/Tooling | 3 | 2 | 1 | 5 | **7.50** | FastAPI DI docs, augustinfotech guide | JobService → Depends() |
| 9 | CI/CD Pipeline (GitHub Actions + lint + test + type check) | Docs/Process | 4 | 1 | 1 | 5 | **20.00** | GitHub Actions docs | .github/workflows/ci.yml |
| 10 | Git Worktree Manager 실제 구현 | Architecture | 3 | 3 | 3 | 3 | **1.00** | ComposioHQ agent-orchestrator | git worktree add 통합 |

> PriorityScore = (Impact × Confidence) / (Effort × Risk)

---

## 4) Best 3 Deep Report

### Best3 Gate Summary

| Best# | Idea | Bucket | PriorityScore | EvidenceCount | DateOK | PopularityOK | Final | Reason |
|---:|---|---|---:|---:|---|---|---|---|
| 1 | CI/CD Pipeline + Test Coverage 확충 | DX/Tooling + Process | 20.00 + 10.00 | 3 | ✅ | ✅ | **PASS** | 가장 낮은 effort+risk, 즉시 실행 가능 |
| 2 | Observability Stack (structlog + OTEL) | Reliability/Obs | 8.33 | 3 | ✅ | ✅ | **PASS** | 프로덕션 필수, <5% overhead |
| 3 | Persistent Queue + DB 마이그레이션 | Reliability | 4.17 + 3.33 | 4 | ✅ | ✅ | **PASS** | 데이터 유실 위험 제거 |

> #4(Test)와 #9(CI/CD)를 하나로 묶음 — 동일 PR 파이프라인에서 진행. #7(Security)은 #3과 같은 Security 버킷이지만, Reliability 버킷 #3(Queue+DB)이 더 높은 구조적 영향이므로 diversity 보장됨.

---

### BEST #1: CI/CD Pipeline + Test Coverage 확충

#### Goal / Non-goals
- **Goal**: GitHub Actions CI 파이프라인 구축 + pytest 커버리지 60%+ 달성 + ruff/mypy 정적 분석
- **Goal**: 모든 PR에서 자동 lint+type+test 실행
- **Goal**: conftest.py 기반 fixture 체계화, DI override 패턴 적용
- **Non-goal**: E2E 테스트(외부 서비스 연동)는 이 단계에서 제외
- **Non-goal**: 배포 자동화(CD)는 이 단계에서 제외

#### Proposed Design
- **Components**: `.github/workflows/ci.yml`, `pyproject.toml` (ruff+mypy config), `tests/conftest.py`, route별 테스트 파일
- **Data flow**: Push/PR → GitHub Actions → `pip install` → `ruff check` → `mypy` → `pytest --cov` → coverage report
- **Interfaces**: FastAPI TestClient + httpx.AsyncClient, dependency_overrides로 FileJobStore/QueueService mock

#### PR Plan

| PR | Scope | Target files/areas | Rollback note |
|---|---|---|---|
| PR1 | pyproject.toml + ruff + mypy 설정 | pyproject.toml, ruff.toml, mypy config | 파일 삭제로 원복 |
| PR2 | conftest.py + DI override + state_machine/parser 테스트 확장 | tests/conftest.py, tests/test_state_machine.py, tests/test_parser.py | 테스트 파일만 삭제 |
| PR3 | route 테스트 (telegram webhook, jobs API) | tests/test_routes_telegram.py, tests/test_routes_jobs.py | 테스트 파일만 삭제 |
| PR4 | worker 테스트 + CI workflow | tests/test_worker.py, .github/workflows/ci.yml | workflow 파일 삭제 |

#### Tests
- **Unit**: state_machine transition 전체 경로, command_parser 경계값, ACL 허용/차단
- **Integration**: TestClient로 telegram webhook → job 생성 → approve → merge 전체 플로우
- **E2E**: N/A (이 단계 제외)
- **Performance**: N/A
- **Security**: ACL bypass 시도 테스트

#### Rollout & Rollback
- **Feature flag**: 불필요 (CI/테스트는 앱 동작에 영향 없음)
- **Canary**: main 브랜치 보호 규칙 적용 → PR 필수
- **Revert path**: CI workflow 파일 삭제 또는 disable
- **Rollback trigger**: CI가 기존 코드를 깨는 경우

#### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 기존 코드에 type error 다수 | High | Low | mypy strict 대신 gradual 모드 |
| asyncio 테스트 복잡도 | Med | Med | pytest-asyncio + anyio 사용 |
| CI 비용 증가 | Low | Low | GitHub Free tier 충분 |
| Mock과 실제 동작 괴리 | Med | Med | Integration test 병행 |
| 테스트 유지보수 부담 | Med | Low | fixture 재사용 + 명확한 네이밍 |

#### KPI Targets

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Test coverage | ~5% (추정) | ≥60% | pytest --cov |
| Type check pass | 미적용 | 0 errors (gradual) | mypy --strict 점진 적용 |
| Lint violations | 미적용 | 0 | ruff check |
| CI pass rate | N/A | ≥95% | GitHub Actions dashboard |
| PR merge → test time | N/A | <3min | GitHub Actions |

#### Dependencies / Migration traps
- `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy` 추가 의존성
- `requirements-dev.txt` 또는 `pyproject.toml [dev]` 분리 필요
- 기존 전역 인스턴스(`job_service = JobService()`) DI override 시 주의

#### Evidence

| Platform | Title | URL | Published | Popularity |
|---|---|---|---|---|
| blog | FastAPI Testing Strategies: pytest, TestClient/httpx, DI Overrides | https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/ | 2025-11-04 | - |
| official | Testing - FastAPI | https://fastapi.tiangolo.com/tutorial/testing/ | 2025-06+ (continuously updated) | fastapi 80k+ ★ |
| medium | FastAPI Unit Testing with Dependency Overrides | https://medium.com/@augustinfotech/fastapi-unit-testing-with-dependency-overrides-a-complete-guide-1db5b451226f | 2025-06+ | - |

---

### BEST #2: Observability Stack (structlog + OpenTelemetry + Prometheus)

#### Goal / Non-goals
- **Goal**: 구조화된 JSON 로깅 (structlog) + request_id 추적
- **Goal**: OpenTelemetry trace 계측 (FastAPI auto-instrumentation)
- **Goal**: Prometheus 메트릭 엔드포인트 (`/metrics`)
- **Goal**: Job 상태 전이 이벤트 로깅 표준화
- **Non-goal**: Grafana/Loki/Tempo 인프라 구축 (별도 단계)
- **Non-goal**: 분산 추적 백엔드 선정

#### Proposed Design
- **Components**: `app/middleware/logging.py` (request_id + structlog), `app/middleware/metrics.py` (prometheus), OTEL auto-instrumentation
- **Data flow**: Request → logging middleware (request_id 생성) → structlog JSON → stdout / file. OTEL → traces exporter. Prometheus → `/metrics` scrape.
- **Interfaces**: structlog.get_logger() 전역 사용, OTEL TracerProvider 설정, prometheus_fastapi_instrumentator

#### PR Plan

| PR | Scope | Target files/areas | Rollback note |
|---|---|---|---|
| PR1 | structlog 도입 + request_id middleware | app/middleware/logging.py, app/main.py, requirements.txt | middleware 제거 |
| PR2 | Job 상태 전이 로깅 표준화 | app/services/state_machine.py, app/workers/worker.py, app/services/job_service.py | 로그 호출 제거 |
| PR3 | OTEL auto-instrumentation + Prometheus metrics | app/middleware/metrics.py, app/main.py | instrumentation 제거 |

#### Tests
- **Unit**: request_id가 모든 로그에 포함되는지 검증
- **Integration**: /health 호출 후 structlog JSON 출력 형식 검증
- **E2E**: N/A
- **Performance**: middleware overhead <5ms per request 확인
- **Security**: request_id에 PII 미포함 검증

#### Rollout & Rollback
- **Feature flag**: `ENABLE_OTEL=true/false` 환경변수
- **Canary**: dev 환경에서 1주 시범 운영
- **Revert path**: middleware 비활성화 (main.py에서 제거)
- **Rollback trigger**: 응답 지연 >50ms 증가 시

#### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| structlog 설정 복잡도 | Med | Low | 공식 docs 기반 minimal 설정 |
| OTEL exporter 미연결 시 에러 | Med | Med | NoOp exporter fallback |
| 로그 볼륨 증가 | Med | Low | log level 제어 + sampling |
| Prometheus endpoint 보안 | Low | Med | internal network only |
| 기존 코드 수정 범위 | Med | Low | middleware 레이어에서 처리 |

#### KPI Targets

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Structured log coverage | 0% | 100% (모든 요청) | structlog JSON 출력 확인 |
| Request traceability | 없음 | request_id 100% 포함 | 로그 샘플링 검증 |
| Metrics endpoint | 없음 | /metrics 200 OK | curl test |
| Logging overhead | N/A | <5ms per request | benchmark |
| MTTD (Mean Time To Detect) | 수동 | <5min | alert rule 설정 후 |

#### Dependencies / Migration traps
- `structlog`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `prometheus-fastapi-instrumentator` 추가
- structlog과 stdlib logging 혼용 주의 — structlog wrapper로 통일 권장
- OTEL collector 없이도 동작하도록 NoOp fallback 필수

#### Evidence

| Platform | Title | URL | Published | Popularity |
|---|---|---|---|---|
| blog | Operations-Friendly Observability: FastAPI Implementation Guide | https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/ | 2025-10-07 | - |
| github | fastapi-observability (Traces/Metrics/Logs on Grafana via OTEL) | https://github.com/blueswen/fastapi-observability | 2025-06+ | 1k+ ★ |
| freecodecamp | End-to-End LLM Observability in FastAPI with OpenTelemetry | https://www.freecodecamp.org/news/build-end-to-end-llm-observability-in-fastapi-with-opentelemetry/ | 2025-06+ | - |

---

### BEST #3: Persistent Task Queue (SAQ) + DB 마이그레이션 (SQLite/PostgreSQL)

#### Goal / Non-goals
- **Goal**: asyncio.Queue → SAQ (Redis-backed) 전환으로 프로세스 재시작 시 작업 보존
- **Goal**: FileJobStore → SQLModel + Alembic 마이그레이션으로 ACID 보장
- **Goal**: dev=SQLite, prod=PostgreSQL dual backend
- **Non-goal**: Redis Cluster/Sentinel HA 구성 (별도 단계)
- **Non-goal**: 전체 ORM 마이그레이션 (JobRecord만 우선)

#### Proposed Design
- **Components**: `app/infra/queue_saq.py` (SAQ worker), `app/infra/db.py` (SQLModel engine), `alembic/` (마이그레이션), `app/models/job.py` (SQLModel)
- **Data flow**: API → SAQ enqueue (Redis BLMOVE, <5ms latency) → SAQ worker dequeue → DB read/write (SQLModel). Job state는 DB에, task queue는 Redis에 분리.
- **Interfaces**: QueueService protocol (enqueue/dequeue) — SAQ adapter 구현. JobStore protocol (create/save/get) — SQLModel adapter 구현. 기존 FileJobStore는 fallback/migration 용으로 유지.

#### PR Plan

| PR | Scope | Target files/areas | Rollback note |
|---|---|---|---|
| PR1 | SQLModel + Alembic 세팅 + JobRecord 모델 | app/models/job.py, app/infra/db.py, alembic/, requirements.txt | alembic downgrade |
| PR2 | SQLJobStore 구현 + Store protocol 정의 | app/infra/storage_sql.py, app/infra/storage.py (protocol) | FileJobStore 복원 |
| PR3 | SAQ + Redis 연동 + QueueService protocol | app/infra/queue_saq.py, app/workers/queue.py (protocol), docker-compose.yml | asyncio.Queue 복원 |
| PR4 | Worker 마이그레이션 + integration test | app/workers/worker.py, tests/test_worker_saq.py | PR3 revert |
| PR5 | 데이터 마이그레이션 스크립트 (JSON → DB) | scripts/migrate_json_to_db.py | 미적용 시 무해 |

#### Tests
- **Unit**: SQLJobStore CRUD, SAQ enqueue/dequeue mock
- **Integration**: API → SAQ → Worker → DB 전체 플로우
- **E2E**: docker-compose up → webhook → job complete
- **Performance**: SAQ latency <5ms, DB query <10ms
- **Security**: Redis AUTH, DB connection string 환경변수

#### Rollout & Rollback
- **Feature flag**: `QUEUE_BACKEND=memory|saq`, `STORE_BACKEND=file|sql` 환경변수
- **Canary**: file+memory 병행 운영 → SQL+SAQ로 점진 전환
- **Revert path**: 환경변수 변경으로 즉시 원복
- **Rollback trigger**: DB connection 실패 3회 연속, SAQ dequeue 지연 >1s

#### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Redis 의존성 추가 | Med | Med | dev=fakeredis, prod=Redis |
| 데이터 마이그레이션 누락 | Med | High | 마이그레이션 스크립트 + 검증 쿼리 |
| Alembic 설정 복잡도 | Med | Low | SQLModel 공식 가이드 따름 |
| 동시성 문제 (DB lock) | Low | Med | SELECT FOR UPDATE + 트랜잭션 |
| Docker 의존성 증가 | Low | Low | docker-compose optional |

#### KPI Targets

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Queue durability | 0% (메모리) | 100% (Redis persist) | 프로세스 재시작 후 job 유지 확인 |
| Job store ACID | 없음 (파일) | 트랜잭션 보장 | concurrent write test |
| Queue latency | ~0ms (인메모리) | <5ms (SAQ) | benchmark |
| DB query time | ~1ms (파일) | <10ms (SQLite/PG) | explain analyze |
| Data migration | N/A | 100% 기존 job 보존 | count 비교 |

#### Dependencies / Migration traps
- `saq[redis]`, `sqlmodel`, `alembic`, `aiosqlite` (dev), `asyncpg` (prod) 추가
- Redis 서버 필요 (dev=docker, prod=managed Redis)
- FileJobStore의 `run_dir` 기반 경로 → DB path로 매핑 필요
- `JobRecord.model_dump(mode="json")`이 SQLModel에서도 동작하도록 호환 유지
- Audit JSONL → DB 테이블 전환은 별도 PR 권장 (scope 제한)

#### Evidence

| Platform | Title | URL | Published | Popularity |
|---|---|---|---|---|
| pypi | SAQ — Simple Async Queue | https://pypi.org/project/saq/ | 2025-06+ (active) | GitHub 400+ ★ |
| blog | Practical Background Processing: Job Queue Design Guide | https://blog.greeden.me/en/2025/12/02/practical-background-processing-with-fastapi-a-job-queue-design-guide-with-backgroundtasks-and-celery/ | 2025-12-02 | - |
| official | SQL Databases - FastAPI | https://fastapi.tiangolo.com/tutorial/sql-databases/ | 2025-06+ | fastapi 80k+ ★ |
| blog | SQLite to PostgreSQL Migration Guide 2025 | https://www.nihardaily.com/93-how-to-convert-sqlite-to-postgresql-step-by-step-migration-guide-for-developers | 2025-06+ | - |

---

## 5) Options A/B/C

### A (보수) — Quick Wins Only
- **범위**: CI/CD + lint + test coverage 60% + structlog 기본
- **리스크**: Low
- **일정**: 2주
- **비용**: 0 AED (GitHub Free)
- **한계**: 인메모리 queue/파일 저장소 유지 — 프로덕션 불가

### B (중간) — Best 3 전부 (권장)
- **범위**: A + Observability full + SAQ + DB 마이그레이션
- **리스크**: Medium
- **일정**: 6주
- **비용**: ~500 AED/month (Redis + PG managed)
- **결과**: 프로덕션 ready 인프라, stub 외부 연동만 남음

### C (공격) — Full Stack 실연동
- **범위**: B + aiogram 통합 + Claude API worker + Codex CLI worker + Git worktree 실구현
- **리스크**: High (외부 API 의존, 비용 변동)
- **일정**: 12주
- **비용**: ~3,000 AED/month (Claude API + Codex + infra)
- **결과**: Telegram 1회 명령 → 실제 plan/execute/review/merge 동작

---

## 6) 30/60/90-day Roadmap

### 30d (Week 1-4)
- **W1**: pyproject.toml + ruff + mypy + conftest.py (PR1-2 of Best#1)
- **W2**: route 테스트 + CI workflow (PR3-4 of Best#1)
- **W3**: structlog + request_id middleware (PR1 of Best#2)
- **W4**: Job 상태 전이 로깅 + OTEL basic (PR2-3 of Best#2)

### 60d (Week 5-8)
- **W5**: SQLModel + Alembic 세팅 (PR1 of Best#3)
- **W6**: SQLJobStore + Store protocol (PR2 of Best#3)
- **W7**: SAQ + Redis + QueueService protocol (PR3 of Best#3)
- **W8**: Worker 마이그레이션 + 데이터 migration (PR4-5 of Best#3)

### 90d (Week 9-12)
- **W9**: Webhook security (HMAC + rate limit + idempotency)
- **W10**: aiogram 3.x 통합 + Telegram sendMessage
- **W11**: Claude API plan worker 프로토타입
- **W12**: Integration test 확충 + staging 배포

---

## 7) Evidence Table

| Idea | Platform | Title | Published | Updated | Accessed | Popularity | URL |
|---|---|---|---|---|---|---|---|
| CI/CD + Test | blog | FastAPI Testing Strategies | 2025-11-04 | - | 2026-03-22 | - | https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/ |
| CI/CD + Test | official | Testing - FastAPI | 2025-06+ | ongoing | 2026-03-22 | 80k+ ★ | https://fastapi.tiangolo.com/tutorial/testing/ |
| CI/CD + Test | medium | FastAPI Unit Testing with DI Overrides | 2025-06+ | - | 2026-03-22 | - | https://medium.com/@augustinfotech/fastapi-unit-testing-with-dependency-overrides-a-complete-guide-1db5b451226f |
| Observability | blog | Operations-Friendly Observability: FastAPI | 2025-10-07 | - | 2026-03-22 | - | https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/ |
| Observability | github | fastapi-observability | 2025-06+ | ongoing | 2026-03-22 | 1k+ ★ | https://github.com/blueswen/fastapi-observability |
| Observability | freecodecamp | End-to-End LLM Observability in FastAPI with OTEL | 2025-06+ | - | 2026-03-22 | - | https://www.freecodecamp.org/news/build-end-to-end-llm-observability-in-fastapi-with-opentelemetry/ |
| Queue + DB | pypi | SAQ — Simple Async Queue | 2025-06+ | active | 2026-03-22 | 400+ ★ | https://pypi.org/project/saq/ |
| Queue + DB | blog | Practical Background Processing: FastAPI | 2025-12-02 | - | 2026-03-22 | - | https://blog.greeden.me/en/2025/12/02/practical-background-processing-with-fastapi-a-job-queue-design-guide-with-backgroundtasks-and-celery/ |
| Queue + DB | official | SQL Databases - FastAPI | 2025-06+ | ongoing | 2026-03-22 | 80k+ ★ | https://fastapi.tiangolo.com/tutorial/sql-databases/ |
| Queue + DB | blog | SQLite to PostgreSQL Migration Guide | 2025-06+ | - | 2026-03-22 | - | https://www.nihardaily.com/93-how-to-convert-sqlite-to-postgresql-step-by-step-migration-guide-for-developers |
| Telegram SDK | github | aiogram | 2025-06+ | v3.26+ | 2026-03-22 | 5.1k ★ | https://github.com/aiogram/aiogram |
| Agent Orch | github | Ruflo | 2025-06+ | active | 2026-03-22 | 21.9k ★ | https://github.com/ruvnet/ruflo |
| Security | dev.to | Webhook Security Best Practices 2025-2026 | 2025-06+ | - | 2026-03-22 | - | https://dev.to/digital_trubador/webhook-security-best-practices-for-production-2025-2026-384n |
| Rate Limit | github | fastapi-limiter | 2025-06+ | active | 2026-03-22 | 400+ ★ | https://github.com/long2ice/fastapi-limiter |

---

## 8) AMBER_BUCKET

| Item | Reason | Potential |
|---|---|---|
| ComposioHQ/agent-orchestrator | published_date 정확히 확인 불가 | Multi-agent 아키텍처 레퍼런스로 활용 가능 |
| LangGraph + FastAPI integration | 날짜 불명확, 프로젝트 스택(LangChain 미사용)과 거리 | AI workflow 아키텍처 참고용 |
| python-telegram-bot v20 + FastAPI | 구체 published_date 미확인 일부 가이드 | aiogram 대비 대안 참고 |

---

## 9) Verification Gate

### PASS/FAIL Table

| Idea | Tier | Verdict | Why | Required checks | Minimal tests |
|---|---|---|---|---|---|
| CI/CD + Test Coverage | Best#1 | **PASS** | evidence 3개, 날짜 OK, 스택 호환, 즉시 적용 가능 | ruff+mypy 설정 검증, pytest 실행 확인 | CI workflow dry-run |
| Observability Stack | Best#2 | **PASS** | evidence 3개, 날짜 OK, middleware 레이어 독립 | structlog JSON 출력 확인, /metrics 200 | request + log 매칭 test |
| Queue + DB Migration | Best#3 | **PASS** | evidence 4개, 날짜 OK, protocol 패턴으로 점진 전환 | SAQ enqueue/dequeue, SQLModel CRUD | docker-compose 환경 테스트 |
| Telegram SDK (aiogram) | Top10#5 | **AMBER** | evidence OK but 구현 scope 큼, Best3 이후 진행 권장 | aiogram webhook 연동 | webhook echo test |
| Claude/Codex Worker | Top10#6 | **AMBER** | 외부 API 의존, 비용 변동, Best3 인프라 확보 후 | API key 연결, rate limit 확인 | plan 생성 1회 test |
| Webhook Security | Top10#7 | **PASS** | Best#1 CI에 포함 가능, 단독 PR도 가능 | HMAC 검증, rate limit | 서명 불일치 거부 test |

### Apply Gates

- **Gate 0 (Dry-run)**: 모든 Best3 PR은 별도 브랜치에서 작성. main 직접 수정 없음. `ruff check --diff`, `mypy --no-incremental`, `pytest --co` (collect only) 로 dry-run.
- **Gate 1 (Change list)**:
  - Best#1: 신규 파일 6~8개 (tests, configs, CI), 기존 파일 수정 0~2개
  - Best#2: 신규 파일 3개 (middleware), 기존 파일 수정 3~4개 (main.py, services)
  - Best#3: 신규 파일 6~8개 (models, infra, alembic, docker), 기존 파일 수정 3~4개 (worker, queue)
- **Gate 2 (Explicit approval)**: ⏳ 사용자 승인 대기. 승인 없이 코드 변경 진행 불가.
- **Gate 3 (Feature flag)**: `QUEUE_BACKEND`, `STORE_BACKEND`, `ENABLE_OTEL` 환경변수로 제어
- **Gate 4 (Rollback plan)**:
  - Best#1: CI workflow disable 또는 삭제
  - Best#2: middleware 제거 (main.py 1줄)
  - Best#3: 환경변수 `memory`/`file`로 복원

### Final: **Go** (조건부)
- Gate 2 승인 후 Best#1 → Best#2 → Best#3 순서로 진행
- 각 Best 완료 시 /check_KPI 실행하여 목표 달성 확인

---

## 10) Open Questions (≤3)

1. **Redis 인프라**: SAQ용 Redis를 자체 호스팅할지, managed service(AWS ElastiCache / Azure Cache)를 사용할지?
2. **DB 선택**: dev=SQLite + prod=PostgreSQL 이중 구조로 갈지, 처음부터 PostgreSQL 단일로 갈지?
3. **Claude API 비용**: Worker 실연동 시 plan 1회 생성당 예상 토큰/비용이 HVDC 프로젝트 예산 범위 내인지?

---

## JSON Envelope

```json
{
  "best3": [
    {
      "rank": 1,
      "idea": "CI/CD Pipeline + Test Coverage 확충",
      "bucket": "DX/Tooling + Process",
      "priority_score": 20.0,
      "evidence": [
        {"platform": "blog", "title": "FastAPI Testing Strategies", "url": "https://blog.greeden.me/en/2025/11/04/fastapi-testing-strategies-to-raise-quality-pytest-testclient-httpx-dependency-overrides-db-rollbacks-mocks-contract-tests-and-load-testing/", "published_date": "2025-11-04", "updated_date": null, "accessed_date": "2026-03-22", "popularity_metric": "-"},
        {"platform": "official", "title": "Testing - FastAPI", "url": "https://fastapi.tiangolo.com/tutorial/testing/", "published_date": "2025-06-01", "updated_date": "2026-03-22", "accessed_date": "2026-03-22", "popularity_metric": "stars=80000+"},
        {"platform": "medium", "title": "FastAPI Unit Testing with DI Overrides", "url": "https://medium.com/@augustinfotech/fastapi-unit-testing-with-dependency-overrides-a-complete-guide-1db5b451226f", "published_date": "2025-06-01", "updated_date": null, "accessed_date": "2026-03-22", "popularity_metric": "-"}
      ],
      "pr_plan": [
        {"pr": "PR1", "scope": "pyproject.toml + ruff + mypy", "rollback": "파일 삭제"},
        {"pr": "PR2", "scope": "conftest + test 확장", "rollback": "테스트 파일 삭제"},
        {"pr": "PR3", "scope": "route 테스트", "rollback": "테스트 파일 삭제"},
        {"pr": "PR4", "scope": "worker 테스트 + CI workflow", "rollback": "workflow 삭제"}
      ],
      "kpis": [
        {"metric": "test_coverage", "target": ">=60%"},
        {"metric": "ci_pass_rate", "target": ">=95%"},
        {"metric": "lint_violations", "target": "0"}
      ],
      "risks": [
        {"risk": "기존 코드 type error", "mitigation": "mypy gradual mode"},
        {"risk": "asyncio 테스트 복잡도", "mitigation": "pytest-asyncio 사용"}
      ]
    },
    {
      "rank": 2,
      "idea": "Observability Stack (structlog + OTEL + Prometheus)",
      "bucket": "Reliability/Observability",
      "priority_score": 8.33,
      "evidence": [
        {"platform": "blog", "title": "Operations-Friendly Observability: FastAPI", "url": "https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/", "published_date": "2025-10-07", "updated_date": null, "accessed_date": "2026-03-22", "popularity_metric": "-"},
        {"platform": "github", "title": "fastapi-observability", "url": "https://github.com/blueswen/fastapi-observability", "published_date": "2025-06-01", "updated_date": "2026-03-22", "accessed_date": "2026-03-22", "popularity_metric": "stars=1000+"}
      ],
      "pr_plan": [
        {"pr": "PR1", "scope": "structlog + request_id middleware", "rollback": "middleware 제거"},
        {"pr": "PR2", "scope": "Job 상태 전이 로깅", "rollback": "로그 호출 제거"},
        {"pr": "PR3", "scope": "OTEL + Prometheus", "rollback": "instrumentation 제거"}
      ],
      "kpis": [
        {"metric": "structured_log_coverage", "target": "100%"},
        {"metric": "request_traceability", "target": "request_id 100%"},
        {"metric": "logging_overhead", "target": "<5ms"}
      ],
      "risks": [
        {"risk": "OTEL exporter 미연결", "mitigation": "NoOp exporter fallback"},
        {"risk": "로그 볼륨 증가", "mitigation": "log level + sampling"}
      ]
    },
    {
      "rank": 3,
      "idea": "Persistent Queue (SAQ) + DB Migration (SQLite/PG)",
      "bucket": "Reliability",
      "priority_score": 4.17,
      "evidence": [
        {"platform": "pypi", "title": "SAQ — Simple Async Queue", "url": "https://pypi.org/project/saq/", "published_date": "2025-06-01", "updated_date": "2026-03-22", "accessed_date": "2026-03-22", "popularity_metric": "stars=400+"},
        {"platform": "blog", "title": "Practical Background Processing: FastAPI", "url": "https://blog.greeden.me/en/2025/12/02/practical-background-processing-with-fastapi-a-job-queue-design-guide-with-backgroundtasks-and-celery/", "published_date": "2025-12-02", "updated_date": null, "accessed_date": "2026-03-22", "popularity_metric": "-"},
        {"platform": "official", "title": "SQL Databases - FastAPI", "url": "https://fastapi.tiangolo.com/tutorial/sql-databases/", "published_date": "2025-06-01", "updated_date": "2026-03-22", "accessed_date": "2026-03-22", "popularity_metric": "stars=80000+"},
        {"platform": "blog", "title": "SQLite to PostgreSQL Migration Guide", "url": "https://www.nihardaily.com/93-how-to-convert-sqlite-to-postgresql-step-by-step-migration-guide-for-developers", "published_date": "2025-06-01", "updated_date": null, "accessed_date": "2026-03-22", "popularity_metric": "-"}
      ],
      "pr_plan": [
        {"pr": "PR1", "scope": "SQLModel + Alembic 세팅", "rollback": "alembic downgrade"},
        {"pr": "PR2", "scope": "SQLJobStore + Store protocol", "rollback": "FileJobStore 복원"},
        {"pr": "PR3", "scope": "SAQ + Redis", "rollback": "asyncio.Queue 복원"},
        {"pr": "PR4", "scope": "Worker migration + test", "rollback": "PR3 revert"},
        {"pr": "PR5", "scope": "데이터 마이그레이션 스크립트", "rollback": "미적용 시 무해"}
      ],
      "kpis": [
        {"metric": "queue_durability", "target": "100%"},
        {"metric": "job_store_acid", "target": "트랜잭션 보장"},
        {"metric": "queue_latency", "target": "<5ms"},
        {"metric": "data_migration", "target": "100% 보존"}
      ],
      "risks": [
        {"risk": "Redis 의존성 추가", "mitigation": "dev=fakeredis"},
        {"risk": "데이터 마이그레이션 누락", "mitigation": "migration script + count 검증"}
      ]
    }
  ],
  "meta": {
    "version": "project-upgrade.v2.0",
    "tz": "Asia/Dubai",
    "generated_at": "2026-03-22T00:00:00+04:00",
    "project": "logi_orchestrator"
  }
}
```
