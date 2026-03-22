# AGENTS.md

## 목적

이 저장소의 에이전트 작업 원칙을 고정한다. 이 문서는 `macho715/logi_orchestrator` 기준이다.

현재 저장소는 **Telegram Gateway + FastAPI Orchestrator + in-memory queue worker + file-based state/artifact store** 골격이다. 실제 Telegram outbound, 실제 Claude/Codex 실행, 실제 `git worktree add`, 실제 merge는 아직 연결되지 않은 **stub v1** 이다.

## 현재 기준선

- 앱명: `logi-orchestrator`
- Python: `>=3.11`
- 핵심 의존성: `fastapi`, `uvicorn[standard]`, `pydantic`, `PyYAML`
- Dev 도구: `ruff`, `pytest`, `pytest-cov`, `pytest-asyncio`, `pre-commit`, `mypy`
- 허용 기본 대상 repo: `macho715/logi_hvdc_dash`
- 타임존 기본값: `Asia/Dubai`

## 시스템 역할 분리

- **Telegram route**: 명령 수신과 command parsing 담당
- **JobService**: ACL, job 생성, 승인, pause/resume/abort 담당
- **QueueWorker**: PLAN/EXEC/TEST/REVIEW/MERGE stub artifact 생성 담당
- **FileJobStore**: `ops/orchestrator/runs/JOB-`* 밑의 `job.json`, `audit/events.jsonl`, artifact 파일 저장
- **ACLService**: `config/acl.yaml` allowlist 검증 담당

## Hard Rules

1. **Gate 우회 금지**
  - Plan 승인 전 write lane 시작 금지
  - Merge 승인 전 완료 처리 금지
2. **상태 계약 보존**
  - `JobState`, `JobEvent`, `transition()`은 저장소의 핵심 계약이다.
  - 새 state/event 추가 시 관련 모듈과 테스트를 반드시 같이 수정한다.
3. **명령 계약 보존**
  - 새 Telegram 명령 추가 시 enum, parser, route, service, docs, tests를 함께 수정한다.
4. **1 writer = 1 worktree**
  - write-capable lane은 같은 worktree를 공유하지 않는다.
  - 현재 구현은 stub 폴더 생성만 하므로, 실제 git worktree로 바꿀 때도 동일 원칙 유지.
5. **Secret/PII 출력 금지**
  - token, cookie, password, webhook secret, chat id 원문, 외부 credential을 artifact나 로그에 남기지 않는다.
6. **구현 범위 과장 금지**
  - 아직 없는 기능을 있는 것처럼 문서화하지 않는다.
  - 특히 `retry`, outbound Telegram, real merge, real Claude/Codex execution은 현재 end-to-end 완성 기능이 아니다.

## 현재 지원 인터페이스

### HTTP

- `GET /health`
- `POST /webhooks/telegram`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/artifacts`
- `POST /jobs/{job_id}/approve-plan`
- `POST /jobs/{job_id}/approve-merge`
- `POST /jobs/{job_id}/pause`
- `POST /jobs/{job_id}/resume`
- `POST /jobs/{job_id}/abort`

### Telegram 명령

- `/project.start repo=... base=... goal="..." ac="..." mode=... priority=...`
- `/status JOB-0001`
- `/approve.plan JOB-0001`
- `/approve.merge JOB-0001`
- `/report JOB-0001`
- `/artifacts JOB-0001`
- `/pause JOB-0001`
- `/resume JOB-0001`
- `/abort JOB-0001`
- `/retry JOB-0001 ...`  ← **예약 상태**. parser/enum은 있으나 service/route/worker 연계가 완료되지 않았다.

## 상태 흐름 기준

기본 흐름은 아래다.

`RECEIVED -> VALIDATED -> PLAN_RUNNING -> PLAN_READY -> PLAN_APPROVAL_WAIT -> FANOUT_QUEUED -> EXEC_RUNNING -> TEST_RUNNING -> REVIEW_RUNNING -> MERGE_APPROVAL_WAIT -> MERGING -> DONE`

예외 흐름은 아래다.

- `VALIDATE_FAIL`, `PLAN_FAIL`, `EXEC_FAIL`, `TESTS_FAIL`, `REVIEW_FAIL`, `MERGE_FAIL` -> `FAILED`
- `PLAN_APPROVAL_WAIT`, `EXEC_RUNNING`, `TEST_RUNNING`, `REVIEW_RUNNING`, `MERGE_APPROVAL_WAIT` -> `PAUSED`
- `PAUSED` 에서 resume target으로 복귀
- 승인 대기/실패 상태에서 `ABORTED` 가능

## 산출물 계약

QueueWorker는 현재 아래 artifact를 만든다.

### plan/

- `PLAN.md`
- `TASKS.yaml`
- `RISKS.md`
- `TESTS.md`

### codex/

- `patch_A.diff`
- `patch_B.diff`
- `impl_A_notes.md`
- `impl_B_notes.md`

### tests/

- `test_results.json`
- `smoke_report.md`

### review/

- `review_summary.md`
- `merge_verdict.json`

### run root

- `final_report.md`
- `job.json`
- `audit/events.jsonl`
- `worktrees/`* (현재는 stub 디렉터리)

## 변경 유형별 필수 수정 포인트

### 1) 명령 변경

수정 파일:

- `app/core/enums.py`
- `app/services/command_parser.py`
- `app/api/routes/telegram.py`
- 필요 시 `app/api/routes/jobs.py`
- `tests/test_parser.py`
- `README.md`
- `ops/orchestrator/telegram_command_spec.md`
- `ops/orchestrator/RUNBOOK.md`

### 2) 상태 전이 변경

수정 파일:

- `app/core/enums.py`
- `app/services/state_machine.py`
- `app/services/job_service.py`
- `app/workers/worker.py`
- `tests/test_state_machine.py`
- `ops/orchestrator/orchestrator_state_machine.md`
- `ops/orchestrator/EVAL.md`
- `ops/orchestrator/RUNBOOK.md`

### 3) artifact 경로/이름 변경

수정 파일:

- `app/workers/worker.py`
- `app/infra/storage.py`
- `README.md`
- `ops/orchestrator/EVAL.md`
- `ops/orchestrator/RUNBOOK.md`

### 4) ACL/권한 변경

수정 파일:

- `config/acl.yaml`
- `app/services/acl.py`
- `README.md`
- webhook 예제 / 운영 문서

## 코딩 원칙

- Python 3.11 문법 기준 유지
- 타입 힌트 유지
- side effect는 service/worker/infra 계층으로 한정
- route는 얇게, 로직은 service로 이동
- 파일 저장 포맷은 UTF-8, JSON은 `ensure_ascii=False`
- 테스트 없이 계약 변경 금지
- 한 PR/한 작업은 한 가지 책임만 바꾼다

## 테스트 원칙

최소 실행:

```bash
pytest
```

권장 실행:

```bash
pytest -v --tb=short --cov=app --cov-report=term-missing
```

변경 범위별 최소 테스트:

- parser 변경: `tests/test_parser.py`
- state 변경: `tests/test_state_machine.py`
- route 변경: webhook/job endpoint smoke test 추가
- worker 변경: artifact 존재성 검증 테스트 추가

## 운영 원칙

- Telegram은 **명령/승인/상태 조회** 채널이다.
- 실제 fan-out과 artifact 생성은 Orchestrator가 담당한다.
- 사람 승인 없이 자동 merge 금지
- queue 재시작 영속화는 아직 없다. 프로세스 재시작 시 in-memory queue는 유실될 수 있다.

## Definition of Done

아래를 모두 만족해야 완료다.

- 관련 테스트 통과
- 상태 전이 계약 훼손 없음
- artifact 경로/이름 문서와 코드가 일치
- README / ops 문서 동기화 완료
- stub와 real 구현 경계를 명확히 표시
- 승인/권한/로그 경로 누락 없음

## 금지 사항

- `JobState` 이름 임의 변경
- route만 바꾸고 parser/test/docs 미수정
- `retry`를 완성 기능처럼 문서화
- `worktree`를 공용 폴더처럼 사용
- secret을 `job.json`, `events.jsonl`, markdown artifact에 기록
- `main` 직접 반영을 전제로 한 설계 작성
