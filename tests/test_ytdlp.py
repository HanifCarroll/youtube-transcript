from __future__ import annotations

import pytest

from youtube_transcript.errors import ToolError
from youtube_transcript.ytdlp import list_caption_tracks, select_track


def sample_info() -> dict:
    return {
        "id": "abc123",
        "title": "Example",
        "subtitles": {
            "en": [{"ext": "json3", "name": "English"}],
            "es": [{"ext": "vtt"}],
        },
        "automatic_captions": {
            "en": [{"ext": "json3"}],
            "fr": [{"ext": "json3"}],
        },
    }


def test_list_caption_tracks_from_structured_metadata() -> None:
    tracks = list_caption_tracks(sample_info())

    assert {track.language for track in tracks} == {"en", "es", "fr"}
    assert any(track.language == "en" and track.source == "manual" for track in tracks)
    assert any(track.language == "en" and track.source == "automatic" for track in tracks)


def test_select_track_prefers_manual() -> None:
    selected, warnings = select_track(sample_info(), language="en", source="any")

    assert selected.source == "manual"
    assert warnings == []


def test_select_track_warns_when_falling_back_to_automatic() -> None:
    selected, warnings = select_track(sample_info(), language="fr", source="any")

    assert selected.source == "automatic"
    assert warnings == ["No manual caption track for language 'fr'. Using automatic captions."]


def test_select_track_requires_exact_language() -> None:
    with pytest.raises(ToolError) as exc:
        select_track(sample_info(), language="en-US", source="any")

    assert "No exact caption track" in exc.value.message
    assert "Available manual tracks: en, es" in exc.value.warnings
