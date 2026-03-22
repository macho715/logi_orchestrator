from app.core.enums import JobCommand
from app.services.command_parser import parse_command


def test_project_start_parser() -> None:
    envelope = parse_command(
        raw_text='/project.start repo=macho715/logi_hvdc_dash base=main goal="ETA KPI" ac="smoke test" mode=default',
        actor="mrcha",
        chat_id=-1001,
        trace_id="tg-1",
    )
    assert envelope.command == JobCommand.PROJECT_START
    assert envelope.args["repo"] == "macho715/logi_hvdc_dash"
    assert envelope.args["goal"] == "ETA KPI"
