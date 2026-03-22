# logi_orchestrator - 구현 계획

> 기반: 20260322_PLAN_DOC_v1.md (90-Day Production Upgrade)

## Phase 1: 인프라 기초 (30일)

### 1-1. CI/CD 파이프라인
- [ ] GitHub Actions 워크플로우 (ruff + mypy + pytest)
- [ ] pre-commit 설정 정리 (ruff-pre-commit, mypy)
- [ ] 커버리지 리포트 (codecov 또는 PR comment)

### 1-2. 테스트 확충 (목표: 60%+)
- [ ] test_job_service.py — create_job, approve_plan, approve_merge, pause, resume, abort
- [ ] test_acl.py — ACLService 전체 메서드
- [ ] test_worker.py — QueueWorker 핸들러별 테스트
- [ ] test_storage.py — FileJobStore CRUD
- [ ] test_audit.py — AuditService write/read
- [ ] test_telegram_route.py — webhook 엔드포인트 통합 테스트
- [ ] conftest.py 정비 (tmp_path 기반 격리)

### 1-3. DI 리팩터링
- [ ] JobService에 store/acl/audit/queue를 생성자 주입
- [ ] QueueWorker에 store/audit/worktrees를 생성자 주입
- [ ] Settings를 FastAPI dependency로 제공
- [ ] 테스트에서 mock/stub 주입 가능하도록

### 1-4. Structured Logging
- [ ] structlog 도입 (JSON 출력)
- [ ] request_id / trace_id 바인딩
- [ ] 모든 상태 전이에 structured log 추가
- [ ] print 문 제거 (ruff T20 규칙 이미 활성)

## Phase 2: 데이터 영속성 + 관측성 (60일)

### 2-1. Persistent Queue (SAQ)
- [ ] SAQ + Redis 의존성 추가
- [ ] QueueService → SAQ 어댑터 교체
- [ ] Worker를 SAQ worker로 전환
- [ ] 프로세스 재시작 후 Job resume 테스트

### 2-2. DB 마이그레이션 (SQLModel + Alembic)
- [ ] SQLModel 모델 정의 (JobRecord, AuditEvent)
- [ ] Alembic 초기화 + 마이그레이션 스크립트
- [ ] FileJobStore → SQLJobStore 교체 (dev=SQLite, prod=PostgreSQL)
- [ ] 기존 file-based 데이터 마이그레이션 스크립트

### 2-3. Observability
- [ ] OpenTelemetry auto-instrumentation (FastAPI)
- [ ] Prometheus metrics 엔드포인트 (/metrics)
- [ ] 핵심 메트릭: job_created_total, job_state_transitions, queue_depth, worker_task_duration

### 2-4. Webhook Security
- [ ] Telegram Bot Token secret 검증
- [ ] Rate limiting (slowapi 또는 커스텀)
- [ ] Idempotency key (trace_id 기반 중복 거부)

## Phase 3: 실연동 + E2E (90일)

### 3-1. aiogram 통합
- [ ] aiogram Bot 인스턴스 + webhook 설정
- [ ] sendMessage 구현 (Plan 보고, 상태 알림, 에러 알림)
- [ ] 메시지 템플릿 (telegram_command_spec.md 5절 기반)
- [ ] 인라인 키보드 (승인 버튼)

### 3-2. Claude API 연동
- [ ] Claude Worker (Plan 생성 — goal/ac/repo context → PLAN.md, TASKS.yaml)
- [ ] Claude Reviewer (diff + test results → review_summary, merge_verdict)
- [ ] Prompt 관리 (버전별 프롬프트 파일)

### 3-3. Codex API 연동
- [ ] Codex Worker (task dispatch → patch/diff 수집)
- [ ] Git worktree 실제 생성 + 격리 실행
- [ ] Sandbox 정책 적용 (workspace-write)

### 3-4. E2E 테스트
- [ ] /project.start → Plan → approve → Exec → Test → Review → approve → Merge 전체 흐름
- [ ] 실패 시나리오 (validation fail, exec fail, test fail)
- [ ] Pause/Resume 시나리오
- [ ] Abort 시나리오

### 3-5. Staging 배포 준비
- [ ] Dockerfile + docker-compose (app + redis + postgres)
- [ ] 환경별 설정 분리 (dev/staging/prod)
- [ ] Health check + graceful shutdown 검증

## 의존성

```
Phase 1 (CI/테스트/DI/로깅)
    ↓
Phase 2 (SAQ/SQLModel/OTEL/보안) — Phase 1 완료 후 진행
    ↓
Phase 3 (aiogram/Claude/Codex/E2E) — Phase 2 완료 후 진행
```

## 우선순위 요약

| 우선순위 | 항목 | 이유 |
|---------|------|------|
| P0 | CI/CD + 테스트 60% | 회귀 방지 없이 리팩터링 불가 |
| P0 | DI 리팩터링 | 테스트 가능성의 전제 조건 |
| P1 | SAQ + SQLModel | 데이터 영속성 = 프로덕션의 최소 조건 |
| P1 | structlog + OTEL | 디버깅/운영 가시성 |
| P2 | aiogram + Claude/Codex | stub을 실연동으로 전환 |
| P2 | E2E 테스트 | 전체 흐름 검증 |
| P3 | Staging 배포 | Phase 3 완료 후 |
