# AGENTS.md

This repo is a small public CLI for source-faithful YouTube transcript capture.

## Public Repo Safety

Do not commit:

- downloaded videos or audio
- fetched transcript artifacts from private or unlisted videos
- cookies, browser profiles, tokens, or private config
- local caches, virtualenvs, or build outputs

Small synthetic fixtures are allowed under `tests/fixtures`.

## Extraction Rules

- Use `yt-dlp` structured metadata and caption files as the source of truth.
- Prefer exact language tracks. Do not broaden `en` to `en.*` silently.
- Prefer manual captions when available, then automatic captions only with an explicit warning.
- Return a clear warning or error when a requested track is missing.
- Do not infer transcript text from page titles, descriptions, broad page text, or search results.

## Verification

Before shipping code changes, run:

```sh
uv run --extra dev ruff check .
uv run --extra dev pytest
uv build
```
