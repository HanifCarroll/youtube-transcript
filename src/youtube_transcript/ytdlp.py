from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ToolError


@dataclass(frozen=True)
class CaptionTrack:
    language: str
    source: str
    formats: list[str]
    name: str | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "language": self.language,
            "source": self.source,
            "formats": self.formats,
        }
        if self.name:
            payload["name"] = self.name
        return payload


@dataclass(frozen=True)
class SelectedTrack:
    language: str
    source: str


@dataclass(frozen=True)
class CookieOptions:
    cookies: Path | None = None
    cookies_from_browser: str | None = None

    def to_ytdlp_args(self) -> list[str]:
        args: list[str] = []
        if self.cookies:
            args.extend(["--cookies", str(self.cookies)])
        if self.cookies_from_browser:
            args.extend(["--cookies-from-browser", self.cookies_from_browser])
        return args


def ytdlp_path() -> str | None:
    return shutil.which("yt-dlp")


def run_ytdlp(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    executable = ytdlp_path()
    if not executable:
        raise ToolError("yt-dlp is not installed or not on PATH.")

    command = [executable, *args]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "yt-dlp failed."
        raise ToolError(message)
    return completed


def dump_info(url: str, *, cookies: CookieOptions | None = None) -> dict[str, Any]:
    cookie_args = (cookies or CookieOptions()).to_ytdlp_args()
    completed = run_ytdlp(
        [
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            *cookie_args,
            url,
        ]
    )
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError("yt-dlp returned invalid JSON metadata.") from exc
    if not isinstance(data, dict):
        raise ToolError("yt-dlp metadata response was not a JSON object.")
    return data


def list_caption_tracks(info: dict[str, Any]) -> list[CaptionTrack]:
    tracks: list[CaptionTrack] = []
    tracks.extend(_tracks_from_section(info.get("subtitles"), source="manual"))
    tracks.extend(_tracks_from_section(info.get("automatic_captions"), source="automatic"))
    source_order = {"manual": 0, "automatic": 1}
    return sorted(tracks, key=lambda track: (source_order[track.source], track.language))


def select_track(
    info: dict[str, Any],
    *,
    language: str,
    source: str,
) -> tuple[SelectedTrack, list[str]]:
    subtitles = info.get("subtitles") if isinstance(info.get("subtitles"), dict) else {}
    automatic = (
        info.get("automatic_captions") if isinstance(info.get("automatic_captions"), dict) else {}
    )
    warnings: list[str] = []

    if source in {"any", "manual"} and language in subtitles:
        return SelectedTrack(language=language, source="manual"), warnings

    if source == "manual":
        raise _missing_track_error(language, subtitles, automatic, requested_source="manual")

    if source in {"any", "automatic"} and language in automatic:
        if source == "any":
            warnings.append(
                f"No manual caption track for language '{language}'. Using automatic captions."
            )
        return SelectedTrack(language=language, source="automatic"), warnings

    if source == "automatic":
        raise _missing_track_error(language, subtitles, automatic, requested_source="automatic")

    raise _missing_track_error(language, subtitles, automatic, requested_source="any")


def download_json3_caption(
    *,
    url: str,
    track: SelectedTrack,
    output_template: Path,
    cookies: CookieOptions | None = None,
) -> Path:
    cookie_args = (cookies or CookieOptions()).to_ytdlp_args()
    write_flag = "--write-subs" if track.source == "manual" else "--write-auto-subs"
    run_ytdlp(
        [
            "--skip-download",
            write_flag,
            "--sub-langs",
            track.language,
            "--sub-format",
            "json3",
            "--output",
            str(output_template),
            *cookie_args,
            url,
        ]
    )
    candidates = sorted(output_template.parent.glob(f"*.{track.language}.json3"))
    if not candidates:
        candidates = sorted(output_template.parent.glob("*.json3"))
    if not candidates:
        raise ToolError(
            f"yt-dlp did not write a json3 caption file for language '{track.language}'."
        )
    if len(candidates) > 1:
        raise ToolError(
            f"yt-dlp wrote multiple json3 caption files for language '{track.language}'."
        )
    return candidates[0]


def _tracks_from_section(section: Any, *, source: str) -> list[CaptionTrack]:
    if not isinstance(section, dict):
        return []
    tracks: list[CaptionTrack] = []
    for language, entries in section.items():
        if not isinstance(language, str) or not isinstance(entries, list):
            continue
        formats = sorted(
            {
                entry.get("ext")
                for entry in entries
                if isinstance(entry, dict) and isinstance(entry.get("ext"), str)
            }
        )
        names = [
            entry.get("name")
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("name"), str)
        ]
        tracks.append(
            CaptionTrack(
                language=language,
                source=source,
                formats=formats,
                name=names[0] if names else None,
            )
        )
    return tracks


def _missing_track_error(
    language: str,
    subtitles: dict[str, Any],
    automatic: dict[str, Any],
    *,
    requested_source: str,
) -> ToolError:
    manual_languages = sorted(subtitles)
    automatic_languages = sorted(automatic)
    warnings = [
        f"Requested source: {requested_source}",
        "Available manual tracks: " + (", ".join(manual_languages) or "none"),
        "Available automatic tracks: " + (", ".join(automatic_languages) or "none"),
    ]
    return ToolError(f"No exact caption track for language '{language}'.", warnings=warnings)
