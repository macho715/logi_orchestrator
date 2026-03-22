# logi_orchestrator - 기능 명세

## Feature 1: Telegram Gateway (Webhook 수신 + 명령 파싱)

### 요구사항
1. Telegram webhook으로 수신된 메시지를 파싱하여 CommandEnvelope 생성
2. `/verb.object` 형식 명령만 허용, 미지원 명령 거부
3. `project.start`는 key=value 인자 파싱, 나머지 명령은 job_id 필수
4. actor(username) 정규화 (@ 제거)

### API 명세
- `POST /webhooks/telegram` — TelegramUpdate JSON 수신 → WebhookAck 응답

### 데이터 모델
- `TelegramUpdate` → `TelegramMessage` → `TelegramChat`, `TelegramUser`
- `CommandEnvelope`: command, raw_text, actor, chat_id, args, trace_id

### 현재 상태
- [x] webhook 엔드포인트 구현
- [x] command_parser 구현
- [ ] 실제 Telegram Bot API sendMessage 미구현
- [ ] webhook secret 검증 미구현
- [ ] aiogram 통합 미구현

---

## Feature 2: Job 상태 머신

### 요구사항
1. 15개 상태 (RECEIVED → DONE/FAILED/ABORTED)
2. 이벤트 기반 전이, 허용되지 않은 전이 시 StateTransitionError
3. Pause/Resume: pause 전 상태를 resume_target_state에 저장, resume 시 복귀
4. Failed → retry (exec/test/review), 최대 2회 재시도

### 비즈니스 로직
- `transition(current, event) → next_state`
- `resume_event_name(target) → resume.{target_name}`
- Terminal states: DONE, ABORTED (진입 후 write task 금지)

### 현재 상태
- [x] _TRANSITIONS dict 완성
- [x] transition() 함수
- [x] resume_event_name() 함수
- [x] 테스트 (test_state_machine.py)

---

## Feature 3: Job 생명주기 (CRUD + 승인)

### 요구사항
1. `create_job`: ACL 검증 → Job 생성 → RECEIVED → VALIDATED → PLAN_RUNNING 자동 전이 → Plan task enqueue
2. `approve_plan`: approver 권한 검증 → FANOUT_QUEUED 전이 → Exec task enqueue
3. `approve_merge`: approver 권한 검증 → MERGING 전이 → Merge task enqueue
4. `pause/resume/abort`: approver 권한 검증 → 상태 전이

### API 명세
- `GET /jobs/{job_id}` — JobRecord 조회
- `POST /jobs/{job_id}/approve-plan` — Plan 승인
- `POST /jobs/{job_id}/approve-merge` — Merge 승인
- `POST /jobs/{job_id}/pause` — 일시정지
- `POST /jobs/{job_id}/resume` — 재개
- `POST /jobs/{job_id}/abort` — 중단

### 데이터 모델
- `JobRecord`: job_id, repo, state, artifacts, retry_count, approved_by, resume_target_state 등
- `AuditEvent`: ts, job_id, from_state, to_state, event, actor, trace_id

### 현재 상태
- [x] JobService 전체 메서드 구현
- [x] FileJobStore (JSON file-based)
- [x] AuditService (JSONL append)
- [ ] DB 영속성 (SQLModel + Alembic) 미구현

---

## Feature 4: Background Queue Worker

### 요구사항
1. asyncio.Queue 기반 비동기 큐
2. task_type별 핸들러: PLAN, EXEC, TEST, REVIEW, MERGE
3. 각 핸들러는 artifact 파일 생성 + 상태 전이 + 다음 task enqueue

### 비즈니스 로직
- PLAN: PLAN.md, TASKS.yaml, RISKS.md, TESTS.md 생성 → PLAN_APPROVAL_WAIT
- EXEC: worktree stub 생성 + patch diff 생성 → TEST enqueue
- TEST: test_results.json + smoke_report.md 생성 → REVIEW enqueue
- REVIEW: review_summary.md + merge_verdict.json 생성 → MERGE_APPROVAL_WAIT
- MERGE: final_report.md 생성 → DONE

### 현재 상태
- [x] QueueWorker + QueueService 구현
- [x] 모든 핸들러 stub 구현
- [ ] 실제 Claude API 연동 미구현
- [ ] 실제 Codex API 연동 미구현
- [ ] SAQ (Redis-backed) 전환 미구현

---

## Feature 5: ACL (접근 제어)

### 요구사항
1. YAML 파일 기반 allowlist (requesters, approvers, operators, repos)
2. 역할별 허용 명령 분리
3. 허용되지 않은 사용자/repo 차단

### 현재 상태
- [x] ACLService 구현
- [x] config/acl.yaml 설정
- [ ] Role-based approval (requester ≠ approver 분리) 미강제

---

## Feature 6: Audit Trail

### 요구사항
1. 모든 상태 전이를 JSONL로 기록
2. 이벤트: ts, job_id, from_state, to_state, event, actor, trace_id
3. runs/JOB-XXXX/audit/events.jsonl에 append

### 현재 상태
- [x] AuditService 구현
- [x] 모든 전이에 audit 기록
- [ ] structured logging (structlog) 미구현
- [ ] OpenTelemetry 미구현
