# telegram_command_spec.md

## 1. 목적

이 문서는 Telegram Gateway Bot의 명령 규격을 정의한다.

Bot은 **사용자 입력을 수집**하고, **Orchestrator API**에 표준 payload를 전달하며, **상태·승인·결과**를 다시 Telegram으로 회신한다.

## 2. 설계 원칙

- 채팅에 노출되는 Bot은 1개만 사용
- 모든 명령은 `/verb.object` 형식 사용
- 모든 쓰기 작업은 승인 게이트 뒤에만 실행
- 모든 응답은 `job_id` 포함
- 모든 명령은 `trace_id`와 `requested_by`를 기록

## 3. 권한 모델

### requester

- `/project.start`
- `/status`
- `/report`
- `/artifacts`

### approver

- `/approve.plan`
- `/approve.merge`
- `/pause`
- `/resume`
- `/abort`

### operator

- `/retry`
- `/requeue`
- `/unlock`
- `/reroute`
- `/cost.guard`

## 4. 명령 목록

## 4.1 `/project.start`

프로젝트를 시작한다.

### 형식

```text
/project.start repo=<repo> base=<branch> goal="<goal>" ac="<acceptance criteria>" mode=<default|burst>
```

### 예시

```text
/project.start repo=macho715/logi_hvdc_dash base=main goal="ETA KPI 탭 추가" ac="필터, export, smoke test" mode=default
```

### 필수 인자

- `repo`
- `base`
- `goal`
- `ac`

### 선택 인자

- `mode`: `default` | `burst`
- `priority`: `low` | `normal` | `high`
- `due`: `YYYY-MM-DD`
- `labels`: comma separated

### 성공 응답

```text
ACK
job_id=JOB-0001
state=RECEIVED
next=PLAN_RUNNING
mode=default
```

### 실패 응답

```text
NACK
reason=INVALID_ARGUMENT
missing=goal
```

## 4.2 `/status`

현재 상태를 조회한다.

### 형식

```text
/status JOB-0001
```

### 성공 응답

```text
JOB-0001
state=PLAN_APPROVAL_WAIT
current_phase=approval_plan
pending=approve.plan
updated_at=2026-03-22T10:15:00+04:00
```

## 4.3 `/approve.plan`

Plan 승인 게이트를 해제한다.

### 형식

```text
/approve.plan JOB-0001
```

### 성공 응답

```text
APPROVED
job_id=JOB-0001
gate=PLAN_APPROVAL
next=FANOUT_QUEUED
```

## 4.4 `/approve.merge`

Merge 승인 게이트를 해제한다.

### 형식

```text
/approve.merge JOB-0001
```

### 성공 응답

```text
APPROVED
job_id=JOB-0001
gate=MERGE_APPROVAL
next=MERGING
```

## 4.5 `/report`

최종 또는 중간 보고서를 조회한다.

### 형식

```text
/report JOB-0001
```

### 성공 응답

```text
REPORT
job_id=JOB-0001
summary=ready
artifacts=7
review=PASS_WITH_WARNINGS
```

## 4.6 `/artifacts`

산출물 목록을 조회한다.

### 형식

```text
/artifacts JOB-0001
```

### 성공 응답

```text
ARTIFACTS
PLAN.md
TASKS.yaml
RISKS.md
TESTS.md
review_summary.md
test_results.json
final_report.md
```

## 4.7 `/pause`

진행 중 Job을 일시정지한다.

### 형식

```text
/pause JOB-0001 reason="human review"
```

### 성공 응답

```text
PAUSED
job_id=JOB-0001
state=PAUSED
```

## 4.8 `/resume`

정지된 Job을 재개한다.

### 형식

```text
/resume JOB-0001
```

### 성공 응답

```text
RESUMED
job_id=JOB-0001
state=EXEC_RUNNING
```

## 4.9 `/abort`

Job을 중단한다.

### 형식

```text
/abort JOB-0001 reason="scope changed"
```

### 성공 응답

```text
ABORTED
job_id=JOB-0001
state=ABORTED
```

## 4.10 `/retry`

실패한 task를 재시도한다.

### 형식

```text
/retry JOB-0001 task=T040
```

### 성공 응답

```text
REQUEUED
job_id=JOB-0001
task=T040
retry_count=1
```

## 4.11 `/requeue`

phase 전체를 다시 queue에 넣는다.

### 형식

```text
/requeue JOB-0001 phase=P40
```

## 4.12 `/reroute`

특정 task의 engine 또는 lane을 바꾼다.

### 형식

```text
/reroute JOB-0001 task=T032 target=CODEX_IMPL_B
```

## 4.13 `/cost.guard`

burst 모드 또는 cloud attempt를 제한한다.

### 형식

```text
/cost.guard JOB-0001 mode=default cloud_attempts=1
```

## 5. 메시지 템플릿

## 5.1 Plan 보고 템플릿

```text
[PLAN READY]
job_id=JOB-0001
repo=macho715/logi_hvdc_dash
goal=ETA KPI 탭 추가
tasks=12
parallel_slots=7
risks=5
action=/approve.plan JOB-0001
```

## 5.2 실행 중간 보고 템플릿

```text
[EXEC UPDATE]
job_id=JOB-0001
phase=fanout_execute
completed=3/4
failed=0
running=T040
next=review
```

## 5.3 Merge 승인 요청 템플릿

```text
[MERGE READY]
job_id=JOB-0001
changed_files=8
tests=PASS
review=PASS_WITH_WARNINGS
rollback=tag/JOB-0001-premerge
action=/approve.merge JOB-0001
```

## 5.4 실패 보고 템플릿

```text
[FAILED]
job_id=JOB-0001
task=T040
reason=unit test failed
next=/retry JOB-0001 task=T040
```

## 6. Webhook Payload

Gateway Bot이 Orchestrator로 전달하는 표준 JSON 예시는 아래와 같다.

```json
{
  "trace_id": "tg-20260322-0001",
  "chat_id": -1001234567890,
  "message_id": 501,
  "requested_by": "@mrcha",
  "role": "requester",
  "command": "project.start",
  "args": {
    "repo": "macho715/logi_hvdc_dash",
    "base": "main",
    "goal": "ETA KPI 탭 추가",
    "ac": "필터, export, smoke test",
    "mode": "default"
  },
  "requested_at": "2026-03-22T10:00:00+04:00"
}
```

## 7. Orchestrator 응답 규격

```json
{
  "trace_id": "tg-20260322-0001",
  "job_id": "JOB-0001",
  "ok": true,
  "state": "PLAN_RUNNING",
  "message": "job accepted",
  "next_action": "wait",
  "artifacts": []
}
```

## 8. 검증 규칙

- 명령어 prefix는 `/`여야 한다.
- verb.object 형식이 아니면 거부한다.
- repo는 allowlist에 있어야 한다.
- approver 명령은 approver role만 허용한다.
- pause 상태에서는 `resume`, `abort`, `status`만 허용한다.
- aborted 상태에서는 `status`, `report`만 허용한다.

## 9. Idempotency 규칙

- 동일 `trace_id`는 1회만 처리한다.
- 동일 `job_id + command + args hash`는 30초 내 중복 거부한다.
- `/approve.plan`, `/approve.merge`는 이미 승인된 경우 NO-OP 응답을 반환한다.

## 10. 오류 코드

| Code | 의미 |
|---|---|
| INVALID_ARGUMENT | 인자 누락 또는 형식 오류 |
| UNAUTHORIZED | 권한 없음 |
| NOT_FOUND | job_id 없음 |
| INVALID_STATE | 현재 상태에서 허용 안 됨 |
| DUPLICATE_REQUEST | 중복 요청 |
| RATE_LIMITED | 요청 과다 |
| INTERNAL_ERROR | 내부 처리 실패 |

## 11. 최소 구현 순서

1. `/project.start`
2. `/status`
3. `/approve.plan`
4. `/approve.merge`
5. `/report`
6. `/retry`
7. `/pause`, `/resume`, `/abort`
