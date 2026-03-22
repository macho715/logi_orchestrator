from __future__ import annotations

import shlex

from app.core.enums import JobCommand
from app.core.exceptions import ValidationError
from app.schemas.job import CommandEnvelope

_SUPPORTED = {command.value: command for command in JobCommand}


def _normalize_actor(username: str | None) -> str:
    if not username:
        return "unknown"
    return username.lstrip("@").strip()


def parse_command(
    *,
    raw_text: str,
    actor: str,
    chat_id: int | None,
    trace_id: str,
) -> CommandEnvelope:
    text = (raw_text or "").strip()
    if not text.startswith("/"):
        raise ValidationError("Telegram 명령은 '/' 로 시작해야 합니다.")

    parts = shlex.split(text)
    if not parts:
        raise ValidationError("빈 명령입니다.")

    name = parts[0].lstrip("/")
    if name not in _SUPPORTED:
        raise ValidationError(f"지원하지 않는 명령입니다: {name}")

    args: dict[str, str] = {}

    if name in {JobCommand.PROJECT_START.value}:
        for token in parts[1:]:
            if "=" not in token:
                raise ValidationError(f"잘못된 인자 형식입니다: {token}")
            key, value = token.split("=", 1)
            args[key] = value
    elif name in {
        JobCommand.STATUS.value,
        JobCommand.APPROVE_PLAN.value,
        JobCommand.APPROVE_MERGE.value,
        JobCommand.REPORT.value,
        JobCommand.ARTIFACTS.value,
        JobCommand.RESUME.value,
    }:
        if len(parts) < 2:
            raise ValidationError("job_id 가 필요합니다.")
        args["job_id"] = parts[1]
    elif name in {JobCommand.PAUSE.value, JobCommand.ABORT.value} or name == JobCommand.RETRY.value:
        if len(parts) < 2:
            raise ValidationError("job_id 가 필요합니다.")
        args["job_id"] = parts[1]
        for token in parts[2:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            args[key] = value

    return CommandEnvelope(
        command=_SUPPORTED[name],
        raw_text=text,
        actor=_normalize_actor(actor),
        chat_id=chat_id,
        args=args,
        trace_id=trace_id,
    )
