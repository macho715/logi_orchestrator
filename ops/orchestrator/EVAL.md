# EVAL.md

## 목적
이 문서는 `macho715/logi_orchestrator` 변경분의 **합격/불합격 기준**을 정의한다. 평가는 기능 추가보다 **계약 보존, 상태 무결성, artifact 일관성, 운영 안전성**을 우선한다.

## 평가 원칙
- **계약 우선**: route, parser, enum, state machine이 서로 맞아야 한다.
- **증거 우선**: 주장보다 test log, artifact, audit log를 본다.
- **stub 경계 명시**: 아직 미구현인 기능은 감점이 아니라, 과장 문서화가 감점이다.
- **운영 안전성 우선**: 승인 게이트, ACL, 로그 누락은 중대 결함으로 본다.

## Verdict
- **PASS**: 계약·테스트·문서·artifact가 모두 정합적이다.
- **PASS_WITH_WARNINGS**: 핵심 흐름은 통과했으나 non-blocking warning이 있다.
- **FAIL**: 상태 전이, 권한, artifact, 테스트 중 하나라도 핵심 결함이 있다.

## Gate Matrix
| No | Gate | Pass Rule | Evidence |
|---:|---|---|---|
| 1 | Interface | route·parser·enum sync | code + test |
| 2 | State | legal transition only | `test_state_machine.py` |
| 3 | ACL | allowlist enforced | config + negative test |
| 4 | Artifact | expected files exist | run dir |
| 5 | Worker | queue flow reaches target state | job.json + audit |
| 6 | Test | pytest pass, cov floor 유지 | test output |
| 7 | Docs | README/ops docs sync | changed docs |
| 8 | Safety | gate bypass 없음 | review |

## 반드시 지켜야 할 현재 계약
### 1. 현재 지원 명령
- `/project.start`
- `/status`
- `/approve.plan`
- `/approve.merge`
- `/report`
- `/artifacts`
- `/pause`
- `/resume`
- `/abort`

`/retry`는 parser와 enum에는 있으나 현재 service/route/worker의 end-to-end 기능으로 완성되지 않았다. 이 점을 무시하고 기능 완료로 평가하면 안 된다.

### 2. 현재 지원 상태
- `RECEIVED`
- `VALIDATED`
- `PLAN_RUNNING`
- `PLAN_READY`
- `PLAN_APPROVAL_WAIT`
- `FANOUT_QUEUED`
- `EXEC_RUNNING`
- `TEST_RUNNING`
- `REVIEW_RUNNING`
- `MERGE_APPROVAL_WAIT`
- `MERGING`
- `DONE`
- `FAILED`
- `PAUSED`
- `ABORTED`

### 3. 현재 artifact 기대치
| 영역 | 파일 |
|---|---|
| plan | `PLAN.md`, `TASKS.yaml`, `RISKS.md`, `TESTS.md`, `agent_assignments.yaml` |
| codex | `patch_A.diff`, `patch_B.diff`, `impl_A_notes.md`, `impl_B_notes.md` |
| tests | `test_results.json`, `smoke_report.md` |
| review | `review_summary.md`, `merge_verdict.json` |
| root | `final_report.md`, `job.json`, `audit/events.jsonl` |

## 필수 Smoke Cases
### Case 1. Health
```bash
curl http://127.0.0.1:8000/health
```
기대:
- HTTP 200
- JSON key `ok`, `service`, `queue_size` 존재

### Case 2. Project start
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
기대:
- `job created`
- `JOB-0001` 생성
- 초기에는 `PLAN_RUNNING`
- worker 처리 후 `PLAN_APPROVAL_WAIT`

### Case 3. Plan approve
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-plan -H "x-actor: mrcha"
```
기대:
- 응답 state `FANOUT_QUEUED`
- 이후 worker 처리로 `EXEC_RUNNING -> TEST_RUNNING -> REVIEW_RUNNING -> MERGE_APPROVAL_WAIT`

### Case 4. Merge approve
```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-merge -H "x-actor: mrcha"
```
기대:
- 응답 state `MERGING`
- 이후 worker 처리로 `DONE`

### Case 5. ACL negative
- `requesters` 밖의 사용자가 `/project.start` 호출하면 400 이어야 한다.
- 허용 repo 목록 밖의 repo를 요청하면 400 이어야 한다.

### Case 6. Invalid transition
- `PLAN_APPROVAL_WAIT` 이전에 `approve-plan` 호출하면 실패해야 한다.
- `PAUSED` 이외 상태에서 `resume` 호출하면 실패해야 한다.

## PASS 기준
아래를 모두 만족하면 PASS다.
1. `pytest` 통과
2. coverage floor `>=10` 유지
3. parser/state 변화 시 관련 테스트 추가 또는 수정
4. state machine dead-end/illegal transition 없음
5. artifact 경로와 이름이 문서와 일치
6. `job.json`과 `audit/events.jsonl`이 실제 생성
7. 승인 게이트 우회 없음
8. README와 ops 문서 동기화 완료

## PASS_WITH_WARNINGS 기준
아래 유형은 warning이다.
- README 문구 일부 경미한 누락
- non-critical artifact 설명 누락
- test는 통과하나 manual smoke note 부재
- dev-only 경고성 lint 수정 미반영

단, 아래는 warning이 아니라 FAIL이다.
- 상태 전이 불일치
- ACL 미작동
- artifact 미생성
- 승인 게이트 우회
- route/parser/docs 불일치
- 미구현 기능을 구현된 것처럼 문서화

## FAIL 기준
하나라도 해당하면 FAIL이다.
- `JobState` 또는 `JobEvent` 추가/변경 후 테스트 미보강
- `/project.start` 또는 승인 흐름이 끊김
- queue worker가 다음 phase로 넘어가지 못함
- `job.json` 또는 `audit/events.jsonl` 누락
- `config/acl.yaml`과 실제 권한 판단이 불일치
- `retry`를 완성 기능처럼 설명
- 실제 git worktree/merge가 아님에도 성공했다고 보고

## Reviewer Checklist
- [ ] route / parser / enum / service sync 확인
- [ ] state transition table 확인
- [ ] smoke case 3개 이상 직접 확인
- [ ] artifact 파일 확인
- [ ] ACL negative case 확인
- [ ] README / RUNBOOK / command spec sync 확인
- [ ] stub vs real 경계 문구 확인

## 권장 로컬 평가 명령
```bash
pytest
ruff check app tests
```

선택:
```bash
mypy app
```

## Known Gaps
현재 저장소는 아래를 아직 제공하지 않는다.
- outbound Telegram `sendMessage`
- 실제 Claude/Codex adapter
- 실제 `git worktree add`
- 실제 merge/PR 생성
- durable queue / restart-safe queue
- `/retry` end-to-end 실행

평가자는 이 공백 자체보다, **공백을 숨기거나 과장하는 문서/코드**를 문제로 봐야 한다.
