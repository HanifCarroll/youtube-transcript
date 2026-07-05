---
name: youtube-transcript
description: Fetch source-faithful YouTube transcripts with the yt-transcript CLI. Use when the user provides a YouTube URL and asks for a transcript, caption capture, transcript artifact, Markdown transcript, JSON transcript, available caption tracks, or a batch transcript run.
---

# YouTube Transcript

Use `yt-transcript` to capture YouTube transcripts from structured caption
tracks. Treat captions as the source of truth; use speech recognition only as an
explicit fallback.

Default artifact destination:

```sh
YOUTUBE_TRANSCRIPT_OUT="/Users/hanifcarroll/Library/Mobile Documents/iCloud~md~obsidian/Documents/hanif-md/inbox/youtube"
```

Use a different `--out` only when the user explicitly requests another
destination.

## Start

Verify the installed command:

```sh
command -v yt-transcript
yt-transcript --json doctor
```

If the command is missing and the repo is available, install it from the checkout:

```sh
cd /Users/hanifcarroll/projects/tools/youtube-transcript
uv tool install --force .
```

Done when `doctor` reports `ok: true` or clearly says `yt-dlp` is missing.

## Caption Path

Inspect tracks before choosing a non-default language:

```sh
yt-transcript --json tracks "https://www.youtube.com/watch?v=VIDEO_ID"
```

Fetch exact-language captions:

```sh
yt-transcript --json fetch "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang en \
  --out "$YOUTUBE_TRANSCRIPT_OUT" \
  --formats txt,md,json
```

Use `--cookies-from-browser chrome` or `--cookies FILE` only when the user is
allowed to access the video and public caption access fails.

Done when the JSON result has `ok: true`, a `source`, a `cue_count`, and output
paths for `metadata`, `txt`, `md`, and `json` when `--out` was requested.

## Batch Path

For a newline-delimited URL file:

```sh
yt-transcript --json batch urls.txt --out "$YOUTUBE_TRANSCRIPT_OUT" --lang en
```

Use `--fail-fast` only when partial output would be worse than stopping on the
first failed video.

Done when `success_count` and `failure_count` account for every requested URL.

## Cleanup Pass

Run this pass after every successful `fetch`, `batch`, or `audio-fallback` run
before summarizing or handing off the transcript.

- Treat `transcript.txt`, `transcript.json`, and `metadata.json` as raw source
  artifacts. Do not edit them.
- Use the generated `transcript.md` as the source for the readable copy. When
  cleanup changes are needed, write `transcript-cleaned.md` beside it, or write
  into the user-requested note path.
- Break the transcript into readable paragraphs by topic, speaker turn, or
  natural pause.
- Apply only high-confidence cleanup: repeated caption fragments, obvious line
  break damage, punctuation, product-name casing, and clear caption
  misrecognitions where the intended phrase is obvious from transcript context.
- Do not guess unclear names, tool names, technical terms, or garbled phrases.
  Mark them as `Needs source check` in the cleaned copy.
- Keep the source metadata and raw artifact links in the cleaned Markdown copy.
- Report the cleaned-copy path, any high-confidence edits made, and any
  remaining `Needs source check` items.

Done when every successful transcript has either a reviewed `transcript.md` with
no changes needed or a `transcript-cleaned.md` / requested note containing the
cleaned readable transcript.

## Fallback

Use `audio-fallback` only when caption tracks are absent, the user asked for
speech recognition, or the transcript must be produced despite caption failure:

```sh
yt-transcript --json audio-fallback "https://www.youtube.com/watch?v=VIDEO_ID" \
  --out "$YOUTUBE_TRANSCRIPT_OUT"
```

This downloads audio and calls `transcribe-audio`, so report that provenance in
the final answer.

## Rules

- Prefer manual captions; automatic-caption fallback is acceptable only when the
  command reports it.
- Keep the requested language exact. Do not broaden `en` to `en.*` silently.
- Do not infer transcript text from title, description, comments, search
  results, or page text.
- Do not summarize a transcript until the raw transcript artifact exists and the
  cleanup pass is complete.
- Keep downloaded media, cookies, and private transcript artifacts out of git.

## Examples

```sh
yt-transcript --json doctor
yt-transcript --json tracks "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
yt-transcript --json fetch "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --out "$YOUTUBE_TRANSCRIPT_OUT"
```
