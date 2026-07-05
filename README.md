# youtube-transcript

Fast YouTube transcripts for agents and local workflows.

`youtube-transcript` installs the `yt-transcript` command. It uses
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp) to fetch YouTube caption tracks
directly, then writes clean text, Markdown, and JSON artifacts that are easy for
an agent to inspect. It is built for the common case where captions already
exist, so you can get a transcript in seconds without downloading video or
running Whisper.

When captions are missing, the tool fails clearly. If you really need speech
recognition, `audio-fallback` is an explicit command that downloads audio and
hands it to `transcribe-audio`.

## Features

- Fast caption-first transcript capture through `yt-dlp`
- Manual captions preferred over automatic captions
- Exact language selection by default, with no broad `en.*` expansion
- Stable `txt`, `md`, and `json` outputs
- `tracks` command for inspecting available manual and automatic caption tracks
- `batch` command for URL lists
- Cookie support for videos your browser can access
- Explicit audio fallback through the local `transcribe-audio` CLI
- Agent-friendly `--json` output and machine-readable errors

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for local install and development
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- Optional: `ffmpeg` for `audio-fallback`
- Optional: `transcribe-audio` for `audio-fallback`

Install `yt-dlp` with Homebrew or your preferred package manager:

```sh
brew install yt-dlp ffmpeg
```

## Install

From this checkout:

```sh
uv tool install --force .
```

Check the local environment:

```sh
yt-transcript --json doctor
```

## Quick Start

List caption tracks:

```sh
yt-transcript --json tracks "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Print a transcript to stdout:

```sh
yt-transcript fetch "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --lang en
```

Write text, Markdown, JSON, and metadata files:

```sh
yt-transcript --json fetch "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --lang en \
  --out ./transcripts \
  --formats txt,md,json
```

Output layout:

```text
transcripts/
  dQw4w9WgXcQ/
    metadata.json
    transcript.json
    transcript.md
    transcript.txt
```

Fetch several videos:

```sh
yt-transcript --json batch urls.txt --out ./transcripts --lang en
```

Use browser cookies when a video requires your logged-in YouTube session:

```sh
yt-transcript --json fetch "https://www.youtube.com/watch?v=..." \
  --cookies-from-browser chrome \
  --out ./transcripts
```

Use the explicit audio fallback:

```sh
yt-transcript --json audio-fallback "https://www.youtube.com/watch?v=..." \
  --out ./transcripts
```

## Commands

| Command | Purpose |
| --- | --- |
| `doctor` | Check required and optional local tools |
| `tracks` | List available manual and automatic caption tracks |
| `fetch` | Fetch one transcript from a caption track |
| `batch` | Fetch transcripts for a newline-delimited URL file |
| `audio-fallback` | Download audio and run `transcribe-audio` explicitly |
| `raw-ytdlp` | Run `yt-dlp` directly when a high-level command is missing |

## Agent Skill

This repo includes a Codex-style companion skill at:

```text
skills/youtube-transcript/SKILL.md
```

Install it into a local Codex skills folder when you want future agents to use
the same transcript workflow:

```sh
cp -R skills/youtube-transcript "${CODEX_HOME:-$HOME/.codex}/skills/youtube-transcript"
```

## JSON Policy

Use `--json` before the command:

```sh
yt-transcript --json doctor
yt-transcript --json fetch "https://www.youtube.com/watch?v=..." --out ./transcripts
```

JSON success output uses this shape:

```json
{
  "ok": true,
  "command": "fetch",
  "video_id": "dQw4w9WgXcQ",
  "title": "Video title",
  "language": "en",
  "source": "manual",
  "cue_count": 42,
  "outputs": {
    "text": "transcripts/dQw4w9WgXcQ/transcript.txt"
  },
  "warnings": []
}
```

JSON errors use this shape and are written to stdout:

```json
{
  "ok": false,
  "error": "No exact caption track for language 'en'.",
  "warnings": ["Available manual tracks: es, pt-BR"]
}
```

Progress and `yt-dlp` diagnostics are not mixed into JSON stdout.

## Source-Faithful Transcript Rules

`yt-transcript` reads YouTube caption metadata and `json3` caption files emitted
by `yt-dlp`.

It does not:

- infer transcript text from page title, description, comments, or visible page
  text
- broaden `--lang en` into `en.*` silently
- hide automatic-caption fallback
- truncate caption cues during extraction
- repair malformed caption JSON

If a requested caption track is unavailable, the command returns a nonzero exit
code and a clear warning with the available track languages.

## Development

```sh
uv run --extra dev ruff check .
uv run --extra dev pytest
uv build
```

Install locally after changes:

```sh
make install-local
```

Smoke-test from outside the repo:

```sh
cd /tmp
command -v yt-transcript
yt-transcript --help
yt-transcript --json doctor
```
