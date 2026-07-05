from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .captions import cues_to_markdown, cues_to_text, parse_json3
from .errors import ToolError
from .output import output_path, print_json, read_json, write_json
from .ytdlp import (
    CookieOptions,
    download_json3_caption,
    dump_info,
    list_caption_tracks,
    run_ytdlp,
    select_track,
    ytdlp_path,
)

VALID_FORMATS = {"txt", "md", "json"}


def main(argv: list[str] | None = None) -> int:
    argv = normalize_argv(list(sys.argv[1:] if argv is None else argv))
    json_output = "--json" in argv
    try:
        args = build_parser().parse_args(argv)
        args.func(args)
        return 0
    except ToolError as err:
        payload = {"ok": False, "error": err.message, "warnings": err.warnings}
        if json_output:
            print_json(payload)
        else:
            print(f"yt-transcript: {err.message}", file=sys.stderr)
            for warning in err.warnings:
                print(f"warning: {warning}", file=sys.stderr)
        return 1


def normalize_argv(argv: list[str]) -> list[str]:
    if "--json" not in argv:
        return argv
    return ["--json", *[arg for arg in argv if arg != "--json"]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-transcript",
        description="Fetch YouTube transcripts from structured caption tracks.",
    )
    parser.add_argument("--json", action="store_true", help="Write machine-readable JSON.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check required and optional tools.")
    doctor.set_defaults(func=cmd_doctor)

    tracks = subparsers.add_parser("tracks", help="List caption tracks for a YouTube URL.")
    tracks.add_argument("url")
    add_cookie_args(tracks)
    tracks.set_defaults(func=cmd_tracks)

    fetch = subparsers.add_parser("fetch", help="Fetch one transcript from captions.")
    fetch.add_argument("url")
    fetch.add_argument("--lang", default="en", help="Exact caption language code.")
    fetch.add_argument(
        "--source",
        choices=["any", "manual", "automatic"],
        default="any",
        help="Caption source. Default: manual when present, otherwise automatic.",
    )
    fetch.add_argument("--out", type=Path, help="Directory for transcript artifacts.")
    fetch.add_argument(
        "--formats",
        default="txt,md,json",
        help="Comma-separated output formats when --out is set: txt,md,json.",
    )
    fetch.add_argument(
        "--timestamps",
        action="store_true",
        help="Include timestamps in txt output.",
    )
    add_cookie_args(fetch)
    fetch.set_defaults(func=cmd_fetch)

    batch = subparsers.add_parser("batch", help="Fetch transcripts for a URL file.")
    batch.add_argument("input", type=Path, help="Newline-delimited URL file.")
    batch.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Directory for transcript artifacts.",
    )
    batch.add_argument("--lang", default="en", help="Exact caption language code.")
    batch.add_argument(
        "--source",
        choices=["any", "manual", "automatic"],
        default="any",
        help="Caption source. Default: manual when present, otherwise automatic.",
    )
    batch.add_argument("--formats", default="txt,md,json")
    batch.add_argument("--timestamps", action="store_true")
    batch.add_argument("--limit", type=int)
    batch.add_argument("--fail-fast", action="store_true")
    add_cookie_args(batch)
    batch.set_defaults(func=cmd_batch)

    fallback = subparsers.add_parser(
        "audio-fallback",
        help="Download audio and run transcribe-audio explicitly.",
    )
    fallback.add_argument("url")
    fallback.add_argument("--out", type=Path, required=True)
    fallback.add_argument("--lang", default="en")
    fallback.add_argument("--model", default="large-v3")
    fallback.add_argument("--backend", default="mlx-whisper")
    add_cookie_args(fallback)
    fallback.set_defaults(func=cmd_audio_fallback)

    raw = subparsers.add_parser("raw-ytdlp", help="Run yt-dlp directly.")
    raw.add_argument("args", nargs=argparse.REMAINDER)
    raw.set_defaults(func=cmd_raw_ytdlp)

    return parser


def add_cookie_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cookies", type=Path, help="Netscape cookies file for yt-dlp.")
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser cookie source passed through to yt-dlp, such as chrome or safari.",
    )


def cookie_options(args: argparse.Namespace) -> CookieOptions:
    return CookieOptions(
        cookies=getattr(args, "cookies", None),
        cookies_from_browser=getattr(args, "cookies_from_browser", None),
    )


def cmd_doctor(args: argparse.Namespace) -> None:
    yt_dlp = ytdlp_path()
    yt_dlp_version = None
    if yt_dlp:
        completed = subprocess.run(
            [yt_dlp, "--version"], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            yt_dlp_version = completed.stdout.strip()

    payload = {
        "ok": bool(yt_dlp),
        "command": "doctor",
        "version": __version__,
        "tools": {
            "yt_dlp": {
                "available": bool(yt_dlp),
                "path": yt_dlp,
                "version": yt_dlp_version,
                "required": True,
            },
            "ffmpeg": {
                "available": bool(shutil.which("ffmpeg")),
                "path": shutil.which("ffmpeg"),
                "required": False,
            },
            "transcribe_audio": {
                "available": bool(shutil.which("transcribe-audio")),
                "path": shutil.which("transcribe-audio"),
                "required": False,
            },
        },
        "auth": {
            "required": False,
            "notes": (
                "Public caption tracks do not require auth. Use --cookies or "
                "--cookies-from-browser for videos your browser can access."
            ),
        },
        "warnings": [] if yt_dlp else ["Install yt-dlp before fetching transcripts."],
    }
    if args.json:
        print_json(payload)
    else:
        print(f"yt-transcript {__version__}")
        print(f"yt-dlp: {yt_dlp_version or 'missing'}")
        print(f"ffmpeg: {'available' if shutil.which('ffmpeg') else 'missing'}")
        print(
            "transcribe-audio: "
            + ("available" if shutil.which("transcribe-audio") else "missing")
        )


def cmd_tracks(args: argparse.Namespace) -> None:
    info = dump_info(args.url, cookies=cookie_options(args))
    tracks = list_caption_tracks(info)
    payload = {
        "ok": True,
        "command": "tracks",
        "video_id": info.get("id"),
        "title": info.get("title"),
        "url": info.get("webpage_url") or args.url,
        "tracks": [track.to_json() for track in tracks],
        "warnings": [],
    }
    if args.json:
        print_json(payload)
        return

    print(f"{payload['title'] or payload['video_id']}")
    if not tracks:
        print("No caption tracks found.")
        return
    for track in tracks:
        formats = ",".join(track.formats) if track.formats else "unknown"
        print(f"{track.language}\t{track.source}\t{formats}")


def cmd_fetch(args: argparse.Namespace) -> None:
    result = fetch_transcript(
        url=args.url,
        language=args.lang,
        source=args.source,
        out=args.out,
        formats=parse_formats(args.formats),
        timestamps=args.timestamps,
        cookies=cookie_options(args),
    )
    if args.json:
        print_json(result)
    elif args.out:
        print(f"Wrote transcript for {result['video_id']} to {result['output_dir']}")
    else:
        print(result["text"])


def cmd_batch(args: argparse.Namespace) -> None:
    urls = read_url_file(args.input)
    if args.limit is not None:
        urls = urls[: args.limit]

    results: list[dict[str, Any]] = []
    failures = 0
    for url in urls:
        try:
            results.append(
                fetch_transcript(
                    url=url,
                    language=args.lang,
                    source=args.source,
                    out=args.out,
                    formats=parse_formats(args.formats),
                    timestamps=args.timestamps,
                    cookies=cookie_options(args),
                )
            )
        except ToolError as err:
            failures += 1
            result = {"ok": False, "url": url, "error": err.message, "warnings": err.warnings}
            results.append(result)
            if args.fail_fast:
                break

    payload = {
        "ok": failures == 0,
        "command": "batch",
        "input": str(args.input),
        "requested_count": len(urls),
        "success_count": len([result for result in results if result.get("ok")]),
        "failure_count": failures,
        "results": results,
        "warnings": [],
    }
    if args.json:
        print_json(payload)
    else:
        print(
            f"Fetched {payload['success_count']} of {payload['requested_count']} transcripts "
            f"into {args.out}"
        )
    if failures:
        raise SystemExit(1)


def cmd_audio_fallback(args: argparse.Namespace) -> None:
    ensure_tool("yt-dlp", required=True)
    ensure_tool("ffmpeg", required=True)
    ensure_tool("transcribe-audio", required=True)

    info = dump_info(args.url, cookies=cookie_options(args))
    video_id = string_field(info, "id", "youtube-video")
    title = string_field(info, "title", video_id)
    run_dir = args.out / video_id
    audio_dir = run_dir / "audio"
    transcript_dir = run_dir / "audio-transcript"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    output_template = audio_dir / "source.%(ext)s"
    run_ytdlp(
        [
            "--extract-audio",
            "--audio-format",
            "m4a",
            "--output",
            str(output_template),
            *cookie_options(args).to_ytdlp_args(),
            args.url,
        ]
    )
    audio_files = sorted(audio_dir.glob("source.*"))
    if not audio_files:
        raise ToolError("yt-dlp did not write an audio file for fallback transcription.")
    audio_file = audio_files[0]

    completed = subprocess.run(
        [
            "transcribe-audio",
            "transcribe",
            str(audio_file),
            "--backend",
            args.backend,
            "--model",
            args.model,
            "--language",
            args.lang,
            "--formats",
            "txt,json",
            "--output-dir",
            str(transcript_dir),
            "--output-name",
            video_id,
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ToolError(
            completed.stderr.strip() or completed.stdout.strip() or "transcribe-audio failed."
        )

    payload = {
        "ok": True,
        "command": "audio-fallback",
        "video_id": video_id,
        "title": title,
        "url": info.get("webpage_url") or args.url,
        "audio": output_path(audio_file),
        "transcribe_audio": json.loads(completed.stdout) if completed.stdout.strip() else None,
        "warnings": [
            (
                "Audio fallback downloaded media and ran speech recognition. Prefer caption "
                "fetch when caption tracks are available."
            )
        ],
    }
    if args.json:
        print_json(payload)
    else:
        print(f"Downloaded audio and wrote fallback transcript under {transcript_dir}")


def cmd_raw_ytdlp(args: argparse.Namespace) -> None:
    raw_args = args.args
    if raw_args and raw_args[0] == "--":
        raw_args = raw_args[1:]
    if not raw_args:
        raise ToolError("raw-ytdlp requires yt-dlp arguments after --.")

    completed = run_ytdlp(raw_args, check=False)
    if args.json:
        print_json(
            {
                "ok": completed.returncode == 0,
                "command": "raw-ytdlp",
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "warnings": [],
            }
        )
    else:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode:
        raise SystemExit(completed.returncode)


def fetch_transcript(
    *,
    url: str,
    language: str,
    source: str,
    out: Path | None,
    formats: set[str],
    timestamps: bool,
    cookies: CookieOptions,
) -> dict[str, Any]:
    info = dump_info(url, cookies=cookies)
    selected, warnings = select_track(info, language=language, source=source)
    video_id = string_field(info, "id", "youtube-video")
    title = string_field(info, "title", video_id)
    webpage_url = string_field(info, "webpage_url", url)

    with tempfile.TemporaryDirectory(prefix="yt-transcript-") as temp_name:
        temp_dir = Path(temp_name)
        caption_file = download_json3_caption(
            url=url,
            track=selected,
            output_template=temp_dir / "%(id)s.%(ext)s",
            cookies=cookies,
        )
        try:
            caption_data = read_json(caption_file)
            cues = parse_json3(caption_data)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ToolError(f"Unable to parse json3 caption file: {exc}") from exc

    text = cues_to_text(cues, timestamps=timestamps)
    metadata = {
        "video_id": video_id,
        "title": title,
        "url": webpage_url,
        "original_url": url,
        "channel": info.get("channel"),
        "duration": info.get("duration"),
        "language": selected.language,
        "source": selected.source,
        "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    transcript = {
        "ok": True,
        "video": {
            "id": video_id,
            "title": title,
            "url": webpage_url,
            "channel": info.get("channel"),
            "duration": info.get("duration"),
        },
        "track": {
            "language": selected.language,
            "source": selected.source,
        },
        "cue_count": len(cues),
        "text": text,
        "cues": [cue.to_json() for cue in cues],
        "warnings": warnings,
    }
    outputs: dict[str, str] = {}
    output_dir = None
    if out:
        output_dir = out / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "metadata.json", {**metadata, "warnings": warnings})
        outputs["metadata"] = output_path(output_dir / "metadata.json")
        if "json" in formats:
            write_json(output_dir / "transcript.json", transcript)
            outputs["json"] = output_path(output_dir / "transcript.json")
        if "txt" in formats:
            text_path = output_dir / "transcript.txt"
            text_path.write_text(text + "\n", encoding="utf-8")
            outputs["txt"] = output_path(text_path)
        if "md" in formats:
            md_path = output_dir / "transcript.md"
            md_path.write_text(
                cues_to_markdown(
                    title=title,
                    url=webpage_url,
                    video_id=video_id,
                    language=selected.language,
                    source=selected.source,
                    cues=cues,
                ),
                encoding="utf-8",
            )
            outputs["md"] = output_path(md_path)

    return {
        "ok": True,
        "command": "fetch",
        "video_id": video_id,
        "title": title,
        "url": webpage_url,
        "language": selected.language,
        "source": selected.source,
        "cue_count": len(cues),
        "text": text,
        "outputs": outputs,
        "output_dir": output_path(output_dir) if output_dir else None,
        "warnings": warnings,
    }


def parse_formats(value: str) -> set[str]:
    formats = {part.strip() for part in value.split(",") if part.strip()}
    if not formats:
        raise ToolError("At least one output format is required.")
    invalid = sorted(formats - VALID_FORMATS)
    if invalid:
        raise ToolError(f"Unsupported output format(s): {', '.join(invalid)}.")
    return formats


def read_url_file(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls


def ensure_tool(name: str, *, required: bool) -> str | None:
    path = shutil.which(name)
    if required and not path:
        raise ToolError(f"{name} is required for this command but is not on PATH.")
    return path


def string_field(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) and value else default


if __name__ == "__main__":
    raise SystemExit(main())
