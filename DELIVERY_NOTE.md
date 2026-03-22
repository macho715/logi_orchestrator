# DELIVERY NOTE

판정: 예

포함:
- FastAPI skeleton
- Telegram webhook endpoint
- JobState enum / state machine helper
- file-based state store
- background queue worker stub
- 기존 PLAN/TASKS/명령/상태머신 문서 동봉

실행:
- `pip install -r requirements.txt`
- `uvicorn app.main:app --reload --port 8000`

주의:
- 현재 버전은 stub
- 실제 Telegram sendMessage, Claude, Codex, Git merge는 후속 연결 필요
