from __future__ import annotations

import json
from pathlib import Path

from youtube_transcript.captions import (
    cues_to_markdown,
    cues_to_text,
    format_timestamp,
    parse_json3,
)


def test_parse_json3_preserves_cue_order_and_text() -> None:
    data = json.loads(Path("tests/fixtures/sample.json3").read_text(encoding="utf-8"))

    cues = parse_json3(data)

    assert [cue.text for cue in cues] == ["First line", "Second line"]
    assert cues[0].start_ms == 1360
    assert cues[0].end_ms == 3040


def test_text_formatting_can_include_timestamps() -> None:
    data = json.loads(Path("tests/fixtures/sample.json3").read_text(encoding="utf-8"))
    cues = parse_json3(data)

    assert cues_to_text(cues) == "First line\nSecond line"
    assert cues_to_text(cues, timestamps=True).splitlines()[0] == "[00:01.360] First line"


def test_markdown_includes_metadata_and_transcript() -> None:
    data = json.loads(Path("tests/fixtures/sample.json3").read_text(encoding="utf-8"))
    cues = parse_json3(data)

    markdown = cues_to_markdown(
        title="Example",
        url="https://youtu.be/example",
        video_id="example",
        language="en",
        source="manual",
        cues=cues,
    )

    assert markdown.startswith("# Example\n")
    assert "- Caption source: `manual`" in markdown
    assert "**00:01.360** First line" in markdown


def test_hour_timestamp_format() -> None:
    assert format_timestamp(3_661_234) == "01:01:01.234"
