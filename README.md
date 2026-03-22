# Telegram + Claude + Codex Orchestrator v1 Skeleton

이 프로젝트는 **Telegram Gateway Bot + FastAPI Orchestrator + background queue worker** 골격이다.

구성 범위:
- FastAPI app skeleton
- Telegram webhook endpoint
- `JobState` enum / state transition helper
- file-based state store / audit log
- background queue worker stub
- Plan / Execute / Test / Review / Merge stub artifact 생성
- 기존 설계 문서 포함

## 빠른 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 기본 엔드포인트

- `GET /health`
- `POST /webhooks/telegram`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/approve-plan`
- `POST /jobs/{job_id}/approve-merge`
- `POST /jobs/{job_id}/pause`
- `POST /jobs/{job_id}/resume`
- `POST /jobs/{job_id}/abort`
- `GET /jobs/{job_id}/artifacts`

## Telegram webhook 테스트 예시

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

## 승인 테스트

```bash
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-plan
curl -X POST http://127.0.0.1:8000/jobs/JOB-0001/approve-merge
```

## 디렉터리

```text
app/
  api/routes/
  core/
  infra/
  schemas/
  services/
  workers/
config/
ops/orchestrator/
tests/
```

## 주의

- 현재 버전은 **stub** 이다.
- 실제 Telegram `sendMessage`, Claude 실행, Codex 실행, Git merge는 구현하지 않았다.
- 대신 동일 인터페이스와 상태 전이, artifact 생성 경로를 먼저 고정했다.
