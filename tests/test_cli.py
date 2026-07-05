from __future__ import annotations

import json

import pytest

from youtube_transcript.cli import main, parse_formats
from youtube_transcript.errors import ToolError


def test_json_doctor_outputs_machine_readable_payload(capsys) -> None:
    exit_code = main(["--json", "doctor"])

    assert exit_code in {0, 1}
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert "yt_dlp" in payload["tools"]


def test_parse_formats_rejects_unknown_format() -> None:
    try:
        parse_formats("txt,pdf")
    except ToolError as exc:
        assert "Unsupported output format" in exc.message
    else:
        raise AssertionError("Expected ToolError")


def test_help_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    assert "fetch" in capsys.readouterr().out
