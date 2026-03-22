# RUNBOOK.md

## 목적
이 문서는 `macho715/logi_orchestrator` v1 stub 운영 절차를 정리한다. 대상은 **운영자, 리뷰어, 구현 에이전트**다.

## 현재 범위
### 포함
- FastAPI app 기동
- Telegram webhook 수신
- job 생성 및 상태 전이
- queue worker 기반 stub artifact 생성
- Plan 승인 / Merge 승인 / pause / resume / abort
- file-based run/audit 저장

### 제외
- 실제 Telegram 발신
- 실제 Claude/Codex 실행
- 실제 git merge
- 실제 `git worktree add`
- durable queue

## 디렉터리 기준
```text
app/
config/
ops/orchestrator/
  PLAN.md
  TASKS.yaml
  telegram_command_spec.md
  orchestrator_state_machine.md
  EVAL.md
  RUNBOOK.md
  runs/
    JOB-0001/
      job.json
      audit/events.jsonl
      plan/
      codex/
      tests/
      review/
      worktrees/
```

## 사전 준비
- Python `>=3.11`
- 가상환경 생성
- `requirements.txt` 설치
- `config/acl.yaml`에 requester/approver/repo 허용값 확인

## 기동 절차
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

앱 기동 시 lifespan hook이 queue worker를 함께 시작한다.

## 기본 확인
### Health
```bash
curl http://127.0.0.1:8000/health
```

기대 key:
- `ok`
- `service`
- `queue_size`

### 허용값 확인
`config/acl.yaml` 기본값은 아래다.
- requester: `mrcha`, `admin`
- approver: `mrcha`, `admin`
- operator: `mrcha`, `admin`
- 허용 repo: `macho715/logi_hvdc_dash`

## 표준 실행 절차
### 1) Job 생성
```bash
curl -X POST http://127.0.0.1:8000/webhooks/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 10,
      "date": 1711000000,
      "chat": {"id": -1001, "type": "group"},
      "from": {"id": 100, "is_bot": false, "username": "mrcha"},
      "text": "/project.start repo=macho715/logi_hvdc_dash base=main goal=\"ETA KPI 탭 추가\" ac=\"필터, export, smoke test\" mode=default"
    }
  }'
```

예상 흐름:
- 응답: `job created`
- `JOB-0001` 생성
- 잠시 뒤 `PLAN_APPROVAL_WAIT`

### 2) 상태 조회
```bash
curl http://127.0.0.1:8000/jobs/JOB-0001
curl http://127.0.0.1:8000/jobs/JOB-0001/artifacts
```

확인 포인트:
- `state`
- `current_phase`
- `artifacts[]`
- `approved_by`
- `run_dir`

### 3) Plan 승인
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-plan -H "x-actor: mrcha"
```

예상 흐름:
- 즉시: `FANOUT_QUEUED`
- 이후: `EXEC_RUNNING -> TEST_RUNNING -> REVIEW_RUNNING -> MERGE_APPROVAL_WAIT`

### 4) Merge 승인
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-merge -H "x-actor: mrcha"
```

예상 흐름:
- 즉시: `MERGING`
- 이후: `DONE`

## 현재 상태 흐름
```text
RECEIVED
 -> VALIDATED
 -> PLAN_RUNNING
 -> PLAN_READY
 -> PLAN_APPROVAL_WAIT
 -> FANOUT_QUEUED
 -> EXEC_RUNNING
 -> TEST_RUNNING
 -> REVIEW_RUNNING
 -> MERGE_APPROVAL_WAIT
 -> MERGING
 -> DONE
```

예외:
- 실패 시 `FAILED`
- 운영 중지 시 `PAUSED`
- 강제 종료 시 `ABORTED`

## Artifact 확인 절차
### plan 확인
- `ops/orchestrator/runs/JOB-0001/plan/PLAN.md`
- `ops/orchestrator/runs/JOB-0001/plan/TASKS.yaml`
- `ops/orchestrator/runs/JOB-0001/plan/RISKS.md`
- `ops/orchestrator/runs/JOB-0001/plan/TESTS.md`

### execute/test/review 확인
- `codex/patch_A.diff`
- `codex/patch_B.diff`
- `tests/test_results.json`
- `tests/smoke_report.md`
- `review/review_summary.md`
- `review/merge_verdict.json`
- `final_report.md`
- `audit/events.jsonl`

## 운영 명령
### pause
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/pause -H "x-actor: mrcha"
```

용도:
- 잘못된 fan-out 중지
- 리뷰 대기 중 수동 점검
- 승인 보류

주의:
- pause는 `PLAN_APPROVAL_WAIT`, `EXEC_RUNNING`, `TEST_RUNNING`, `REVIEW_RUNNING`, `MERGE_APPROVAL_WAIT` 에서만 유효하다.

### resume
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/resume -H "x-actor: mrcha"
```

주의:
- `PAUSED` 상태에서만 가능
- resume target은 저장된 `resume_target_state` 로 복귀한다.

### abort
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/abort -H "x-actor: mrcha"
```

용도:
- 승인 취소
- 실패 job 종료
- 잘못 생성된 job 폐기

## 장애 대응
| 증상 | 원인 후보 | 1차 조치 | 2차 조치 |
|---|---|---|---|
| 400 requester 권한 없음 | ACL 불일치 | `config/acl.yaml` 확인 | username 정규화 확인 |
| 400 허용되지 않은 repo | allowlist 미등록 | repo 값 확인 | `repos` 추가 |
| 400 허용되지 않은 전이 | 잘못된 승인 타이밍 | 현재 `state` 조회 | state machine/doc 동기화 |
| `PLAN_RUNNING` 장기 정체 | worker 미기동 | 앱 재기동 | queue/log 확인 |
| artifact 없음 | worker 실패 | `job.json`, `events.jsonl` 확인 | worker 단계 재현 |
| resume 실패 | PAUSED 아님 | 현재 상태 확인 | pause 후 resume |
| DONE인데 merge 기대 | stub 한계 오해 | README/RUNBOOK 확인 | real merge adapter 별도 구현 |

## 수동 점검 포인트
### `job.json`
- state
- previous_state
- resume_target_state
- current_phase
- artifacts
- approved_by

### `audit/events.jsonl`
- 상태 전이 순서
- actor
- trace_id
- detail

### `worktrees/`
현재는 실제 git worktree가 아니라 stub 디렉터리다. 운영자와 리뷰어는 이 점을 반드시 인지해야 한다.

## 재기동/복구 주의
현재 queue는 `asyncio.Queue` 기반 in-memory 구조다. 따라서 프로세스를 재시작하면 queue 자체는 유지되지 않는다.

복구 원칙:
1. `job.json`으로 마지막 상태 확인
2. `audit/events.jsonl`로 전이 이력 확인
3. 필요한 경우 새 job을 생성하거나 수동 recovery patch 작성
4. durable queue 구현 전까지 restart-safe 운영을 가정하지 않는다

## 변경 관리
아래 변경 시 문서도 같이 갱신한다.
- 명령 추가/삭제
- 상태 추가/삭제
- artifact 이름/경로 변경
- ACL 변경
- health/webhook/job endpoint 변경

필수 동기화 파일:
- `README.md`
- `AGENTS.md`
- `ops/orchestrator/telegram_command_spec.md`
- `ops/orchestrator/orchestrator_state_machine.md`
- `ops/orchestrator/EVAL.md`
- `ops/orchestrator/RUNBOOK.md`

## ZERO 규칙
- Plan 승인 없이 execute 강행 금지
- Merge 승인 없이 완료/반영 보고 금지
- `retry`를 구현된 기능처럼 운영 금지
- 실제 merge가 없는데 merge 성공으로 외부 보고 금지
- secret/PII를 artifact와 audit에 기록 금지
- 같은 worktree에 다중 writer 투입 금지
