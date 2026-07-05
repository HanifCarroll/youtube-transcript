from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Cue:
    start_ms: int
    duration_ms: int
    text: str

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms

    def to_json(self) -> dict[str, Any]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "start": format_timestamp(self.start_ms),
            "end": format_timestamp(self.end_ms),
            "text": self.text,
        }


def parse_json3(data: dict[str, Any]) -> list[Cue]:
    events = data.get("events")
    if not isinstance(events, list):
        raise ValueError("Caption JSON does not contain an events list.")

    cues: list[Cue] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        segments = event.get("segs")
        if not isinstance(segments, list):
            continue

        source_text = "".join(
            segment.get("utf8", "") for segment in segments if isinstance(segment, dict)
        )
        text = normalize_caption_text(source_text)
        if not text:
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)
        if not isinstance(start_ms, int) or not isinstance(duration_ms, int):
            continue

        cues.append(Cue(start_ms=start_ms, duration_ms=duration_ms, text=text))

    return cues


def normalize_caption_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def cues_to_text(cues: list[Cue], *, timestamps: bool = False) -> str:
    lines = []
    for cue in cues:
        if timestamps:
            lines.append(f"[{format_timestamp(cue.start_ms)}] {cue.text}")
        else:
            lines.append(cue.text)
    return "\n".join(lines).strip()


def cues_to_markdown(
    *,
    title: str,
    url: str,
    video_id: str,
    language: str,
    source: str,
    cues: list[Cue],
) -> str:
    lines = [
        f"# {title or video_id}",
        "",
        f"- Source: {url}",
        f"- Video ID: `{video_id}`",
        f"- Language: `{language}`",
        f"- Caption source: `{source}`",
        "",
        "## Transcript",
        "",
    ]
    for cue in cues:
        lines.append(f"**{format_timestamp(cue.start_ms)}** {cue.text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_timestamp(milliseconds: int) -> str:
    total_seconds, ms = divmod(milliseconds, 1000)
    minutes_total, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes_total, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    return f"{minutes:02d}:{seconds:02d}.{ms:03d}"
