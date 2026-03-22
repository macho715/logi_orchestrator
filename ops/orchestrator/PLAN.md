# PLAN.md

## 1. 프로젝트 개요

- 프로젝트명: Telegram + Claude + Codex 멀티에이전트 Orchestrator v1
- 대상 저장소: `macho715/logi_hvdc_dash`
- 기본 브랜치: `main`
- 기준 타임존: `Asia/Dubai`
- 운영 원칙: **Telegram=관제**, **Claude=Plan/Review**, **Codex=Execute/Test**
- 승인 게이트: **Plan 승인 1회 + Merge 승인 1회**

> ⚠️AMBER:[가정] 저장소명은 `macho715/logi_hvdc_dash`로 가정했다. 실제 저장소가 다르면 `repo`, `base_branch`, `path_prefix`만 교체하면 된다.

## 2. 목표

이 프로젝트의 목표는 Telegram 그룹 명령 1회로 프로젝트를 시작하고, Claude와 Codex를 병렬로 fan-out하여 Plan, 구현, 테스트, 리뷰, 보고까지 자동화하는 것이다.

최종적으로 사용자는 Telegram에서 아래 4가지만 수행한다.

1. 프로젝트 시작
2. Plan 승인
3. Merge 승인
4. 결과 보고 확인

## 3. 범위

### 포함

- Telegram Gateway Bot
- Orchestrator API / Worker / Queue / State Store
- Claude Lane
  - Plan 생성
  - 리뷰 기준 생성
  - 최종 리뷰 요약
- Codex Lane
  - 구현 fan-out
  - 테스트 fan-out
  - patch/diff 수집
- Git worktree 격리
- Audit log
- Job report

### 제외

- 결제, 배포, 외부 서비스 생성
- production secret 자동 주입
- 무승인 merge
- 같은 worktree에서 다중 write

## 4. 성공 기준

### 기능 성공 기준

- `/project.start` 1회로 Job 생성
- `PLAN.md`, `TASKS.yaml`, `RISKS.md`, `TESTS.md` 자동 생성
- 승인 전에는 write lane 미실행
- 승인 후 Codex worktree 2개 이상 병렬 실행
- 테스트 결과와 diff 요약 자동 보고
- Merge 승인 전에는 기본 브랜치 반영 금지

### 운영 성공 기준

- Job 상태 추적 가능
- 실패 task 재시도 가능
- 모든 명령에 audit trail 존재
- 승인자와 실행자 분리 가능
- Telegram 메시지 하나로 현재 상태 조회 가능

## 5. 아키텍처

```text
[Telegram Group]
    │
    ▼
[Gateway Bot]
    │ webhook
    ▼
[Orchestrator API]
    ├─ Auth / ACL
    ├─ Command Parser
    ├─ Job State Machine
    ├─ Queue Dispatcher
    └─ Report Builder
          │
          ├───────────────┬────────────────┬───────────────┐
          ▼               ▼                ▼               ▼
   [State Store]     [Audit Store]   [Artifact Store]   [Queue]
                                                          │
                                       ┌──────────────────┴─────────────────┐
                                       ▼                                    ▼
                               [Claude Worker]                       [Codex Worker]
                                       │                                    │
                            Plan / Review / Risk                 Impl / Test / Patch
                                       │                                    │
                                       └───────────[Git Worktree Manager]───┘
                                                         │
                                                         ▼
                                                   [Target Repo]
```

## 6. 에이전트 역할 정의

### Claude Lane

- **Claude Lead**
  - 입력: goal, acceptance criteria, repo context
  - 출력: `PLAN.md`, `TASKS.yaml`, `RISKS.md`, `TESTS.md`
- **Claude Architect**
  - 입력: approved plan
  - 출력: option compare, design notes
- **Claude Reviewer**
  - 입력: diff, test result, changed files
  - 출력: review summary, merge verdict

### Codex Lane

- **Codex Lead**
  - 입력: approved plan, task graph
  - 출력: executable task dispatch
- **Codex Impl-A**
  - 역할: 기능 구현 A
- **Codex Impl-B**
  - 역할: 기능 구현 B
- **Codex Tester**
  - 역할: lint, unit, smoke test
- **Codex Cloud Attempt-N**
  - 역할: heavy refactor 또는 대안 구현

## 7. 병렬 실행 정책

### 기본 슬롯

- Claude Lead: 1
- Claude Architect/Reviewer: 2
- Codex Lead: 1
- Codex Impl: 2
- Codex Tester: 1
- Codex Cloud Attempt: 1

**기본 동시 슬롯 = 7**

### Burst 슬롯

- Claude QA: +1
- Codex Cloud Attempt: +2
- Codex Test Parallel: +1

**Burst 동시 슬롯 = 11**

### 강제 규칙

- write-capable agent는 **1 worktree = 1 agent**
- Plan 승인 전 Codex write lane 금지
- Merge 승인 전 main 반영 금지
- 실패 task는 최대 2회 재시도
- 2회 실패 시 human review로 전환

## 8. 저장소 구조

```text
ops/
  orchestrator/
    PLAN.md
    TASKS.yaml
    telegram_command_spec.md
    orchestrator_state_machine.md
    RISKS.md
    TESTS.md
    reports/
    runs/
      JOB-0001/
        plan/
        review/
        codex/
        tests/
        audit/
app/
workers/
infra/
```

## 9. 승인 게이트

### Gate 1: Plan 승인

조건:
- `PLAN.md` 생성 완료
- `TASKS.yaml` 생성 완료
- 주요 리스크 명시
- 병렬 fan-out 대상 식별 완료

Telegram 승인 명령:

```text
/approve.plan JOB-0001
```

### Gate 2: Merge 승인

조건:
- 구현 task 종료
- 테스트 결과 수집 완료
- 리뷰 결과 `PASS` 또는 `PASS_WITH_WARNINGS`
- rollback 포인트 명시

Telegram 승인 명령:

```text
/approve.merge JOB-0001
```

## 10. 산출물 정의

### Job 공통 산출물

- `PLAN.md`
- `TASKS.yaml`
- `RISKS.md`
- `TESTS.md`
- `diff_summary.md`
- `review_summary.md`
- `final_report.md`

### 실행 로그

- `audit/events.jsonl`
- `audit/commands.jsonl`
- `audit/approvals.jsonl`
- `audit/transitions.jsonl`

## 11. 비기능 요건

### 보안

- Telegram 허용 사용자 allowlist
- secret은 `.env` 또는 vault에서만 로드
- chat에 token, password, cookie 출력 금지
- 작업 transcript에는 secret masking 적용

### 안정성

- 모든 command는 idempotency key 지원
- webhook 처리와 worker 처리는 분리
- queue 재시작 후 job resume 가능

### 감사성

- 누가 시작했는지 기록
- 누가 승인했는지 기록
- 어떤 diff가 merge됐는지 기록
- 어떤 agent가 어떤 task를 수행했는지 기록

## 12. 리스크와 대응

### 주요 리스크

1. 같은 파일에 동시 write 충돌
   - 대응: worktree 분리, file lock, merge 전 rebase
2. Plan 없이 구현 선행
   - 대응: Gate 1 강제
3. 과도한 병렬 실행으로 비용 증가
   - 대응: 기본 7-slot, burst는 명시 요청 시만 활성화
4. Telegram 오입력
   - 대응: command validation, dry-run preview
5. 테스트 미실행 상태 merge
   - 대응: Gate 2 강제, test artifact 필수

## 13. 실행 순서

1. Gateway Bot 생성
2. `/project.start` 수신
3. Job 생성 및 VALIDATED 전환
4. Claude Lead로 Plan 생성
5. Plan 보고 및 승인 대기
6. 승인 후 Codex lane fan-out
7. 테스트와 리뷰 병렬 수행
8. 최종 보고 및 Merge 승인 대기
9. 승인 후 merge 또는 PR 생성
10. 완료 보고 및 archive

## 14. Definition of Done

아래 조건을 모두 만족하면 완료로 본다.

- 승인 2회 완료
- 구현/테스트/review artifact 존재
- 상태가 `DONE` 또는 `MERGED`
- audit trail 누락 없음
- rollback 포인트 존재

## 15. v1 구현 우선순위

### P1

- Telegram Gateway
- Orchestrator API
- State Machine
- Queue
- Claude Plan lane
- Codex Execute/Test lane
- Worktree manager
- Report builder

### P2

- Retry 정책
- Cost guard
- Role-based approval
- Report template 개선

### P3

- Multi-repo
- Cost forecast
- OOG/WH/KPI 특화 template
- Slack/Email bridge
