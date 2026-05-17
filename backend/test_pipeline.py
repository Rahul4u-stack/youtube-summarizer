"""Unit tests for the pipeline functions.

Heavy I/O (yt-dlp, whisper, Anthropic) is mocked. Real end-to-end testing
happens via a manual curl in Phase 2 verification.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import pipeline
from pipeline import (
    download_audio,
    transcribe,
    summarize,
    run_pipeline,
    DownloadError,
    TranscribeError,
    SummarizeError,
)


# ---------- summarize() ----------

def _mock_claude_response(text: str, cache_read: int = 0, cache_create: int = 0,
                          input_tok: int = 100, output_tok: int = 200) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    usage = MagicMock()
    usage.cache_read_input_tokens = cache_read
    usage.cache_creation_input_tokens = cache_create
    usage.input_tokens = input_tok
    usage.output_tokens = output_tok
    response.usage = usage
    return response


def test_summarize_parses_clean_json():
    claude_text = json.dumps({
        "executive_summary": "Two paragraphs of summary.",
        "key_insights": ["a", "b", "c", "d", "e"],
        "action_items": ["x"],
        "topics_covered": ["tag1", "tag2", "tag3"],
        "tone": "tutorial",
    })
    client = MagicMock()
    client.messages.create.return_value = _mock_claude_response(claude_text, cache_create=10000)

    summary, usage = summarize("hello world", "My Video", client)

    assert summary.executive_summary == "Two paragraphs of summary."
    assert len(summary.key_insights) == 5
    assert summary.action_items == ["x"]
    assert summary.tone == "tutorial"
    assert usage["cache_hit"] is False  # first call -> cache_create > 0, cache_read == 0
    assert usage["tokens_used"] > 0


def test_summarize_detects_cache_hit():
    claude_text = json.dumps({
        "executive_summary": "s", "key_insights": ["a"],
        "action_items": [], "topics_covered": ["t1", "t2", "t3"], "tone": None,
    })
    client = MagicMock()
    # second call: cache_read > 0 means we hit the cache
    client.messages.create.return_value = _mock_claude_response(
        claude_text, cache_read=10000, cache_create=0,
    )

    _, usage = summarize("hello", "v", client)
    assert usage["cache_hit"] is True
    assert usage["cache_read_tokens"] == 10000


def test_summarize_extracts_json_from_surrounding_prose():
    # Claude sometimes wraps despite instructions
    claude_text = (
        "Sure! Here's the summary:\n\n"
        '{"executive_summary": "s", "key_insights": ["a"], '
        '"action_items": [], "topics_covered": ["t1","t2","t3"], "tone": "casual"}\n\n'
        "Let me know if you need more!"
    )
    client = MagicMock()
    client.messages.create.return_value = _mock_claude_response(claude_text)
    summary, _ = summarize("hello", "v", client)
    assert summary.tone == "casual"


def test_summarize_empty_transcript_raises():
    client = MagicMock()
    with pytest.raises(SummarizeError, match="empty"):
        summarize("   ", "v", client)


def test_summarize_handles_malformed_response():
    client = MagicMock()
    client.messages.create.return_value = _mock_claude_response("totally not json")
    with pytest.raises(SummarizeError):
        summarize("hello", "v", client)


def test_summarize_handles_empty_response():
    client = MagicMock()
    empty = MagicMock()
    empty.content = []
    client.messages.create.return_value = empty
    with pytest.raises(SummarizeError, match="Empty"):
        summarize("hello", "v", client)


def test_summarize_uses_cache_control():
    """The transcript content block must carry cache_control: ephemeral."""
    claude_text = json.dumps({
        "executive_summary": "s", "key_insights": ["a"],
        "action_items": [], "topics_covered": ["t1", "t2", "t3"], "tone": "casual",
    })
    client = MagicMock()
    client.messages.create.return_value = _mock_claude_response(claude_text)
    summarize("a transcript", "title", client)

    call_kwargs = client.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    transcript_block = user_content[0]
    assert transcript_block["cache_control"] == {"type": "ephemeral"}, \
        "transcript block must be marked cacheable so repeat calls are cheap"


# ---------- transcribe() ----------

def test_transcribe_missing_audio_file_raises(tmp_path):
    with pytest.raises(TranscribeError, match="not found"):
        transcribe(tmp_path / "nope.wav")


def test_transcribe_missing_model_raises(tmp_path, monkeypatch):
    fake_audio = tmp_path / "audio.wav"
    fake_audio.write_bytes(b"RIFF....")
    monkeypatch.setattr(pipeline, "WHISPER_MODEL", "/no/such/model.bin")
    with pytest.raises(TranscribeError, match="model not found"):
        transcribe(fake_audio)


def _patch_whisper_paths(monkeypatch, tmp_path):
    """Point WHISPER_BIN and WHISPER_MODEL at real files in tmp_path so
    transcribe()'s existence checks pass on every CI runner — the default
    paths are macOS-specific (/opt/homebrew/...) and fail on Linux."""
    fake_bin = tmp_path / "whisper-bin"
    fake_bin.write_bytes(b"#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)
    fake_model = tmp_path / "model.bin"
    fake_model.write_bytes(b"x")
    monkeypatch.setattr(pipeline, "WHISPER_BIN", str(fake_bin))
    monkeypatch.setattr(pipeline, "WHISPER_MODEL", str(fake_model))


def test_transcribe_parses_whisper_json(tmp_path, monkeypatch):
    _patch_whisper_paths(monkeypatch, tmp_path)
    fake_audio = tmp_path / "audio.wav"
    fake_audio.write_bytes(b"RIFF....")

    # whisper.cpp writes audio.wav.json beside the audio file
    json_out = fake_audio.with_suffix(fake_audio.suffix + ".json")
    json_out.write_text(json.dumps({
        "transcription": [
            {"text": " hello "},
            {"text": " world "},
            {"text": " from whisper. "},
        ]
    }))

    proc = MagicMock(returncode=0, stderr="")
    with patch.object(pipeline.subprocess, "run", return_value=proc):
        result = transcribe(fake_audio)

    assert result["full_text"] == "hello world from whisper."
    assert result["word_count"] == 4
    assert result["language"] == "en"


def test_transcribe_handles_nonzero_returncode(tmp_path, monkeypatch):
    _patch_whisper_paths(monkeypatch, tmp_path)
    fake_audio = tmp_path / "audio.wav"
    fake_audio.write_bytes(b"x")

    proc = MagicMock(returncode=1, stderr="whisper exploded")
    with patch.object(pipeline.subprocess, "run", return_value=proc):
        with pytest.raises(TranscribeError, match="whisper exploded"):
            transcribe(fake_audio)


# ---------- download_audio() ----------

def test_download_audio_wraps_yt_dlp_errors(tmp_path):
    import yt_dlp
    with patch.object(pipeline.yt_dlp, "YoutubeDL") as mock_ydl_cls:
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("video unavailable")
        mock_ydl_cls.return_value = mock_ydl

        with pytest.raises(DownloadError, match="Couldn't download"):
            download_audio("https://www.youtube.com/watch?v=xxxxxxxxxxx", tmp_path)


def test_download_audio_returns_path_and_metadata(tmp_path):
    expected_wav = tmp_path / "audio.wav"
    expected_wav.write_bytes(b"RIFF....fake wav")

    fake_info = {
        "title": "Test Video",
        "channel": "Test Channel",
        "duration": 120,
        "thumbnail": "https://img.example/t.jpg",
    }

    with patch.object(pipeline.yt_dlp, "YoutubeDL") as mock_ydl_cls:
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = fake_info
        mock_ydl_cls.return_value = mock_ydl

        path, info = download_audio("https://www.youtube.com/watch?v=xxxxxxxxxxx", tmp_path)

    assert path == expected_wav
    assert info["title"] == "Test Video"


# ---------- run_pipeline() ----------

def test_run_pipeline_full_happy_path(tmp_path):
    """Mocks all 3 stages and verifies SummaryPayload assembly."""
    expected_wav = tmp_path / "audio.wav"
    expected_wav.write_bytes(b"x")

    fake_info = {
        "title": "Stanford CS229",
        "channel": "Stanford Online",
        "duration": 3600,
        "thumbnail": "https://t.example/x.jpg",
    }
    fake_summary_json = json.dumps({
        "executive_summary": "ML lecture overview.",
        "key_insights": ["a", "b", "c", "d", "e"],
        "action_items": ["read chapter 1"],
        "topics_covered": ["machine learning", "stanford", "lecture"],
        "tone": "academic",
    })

    client = MagicMock()
    client.messages.create.return_value = _mock_claude_response(fake_summary_json, cache_create=15000)

    with patch.object(pipeline, "download_audio", return_value=(expected_wav, fake_info)), \
         patch.object(pipeline, "transcribe", return_value={
             "full_text": "Welcome to CS229. Today we cover supervised learning.",
             "word_count": 9,
             "language": "en",
         }):
        result = run_pipeline("https://www.youtube.com/watch?v=xxxxxxxxxxx", tmp_path, client)

    assert result["video"]["title"] == "Stanford CS229"
    assert result["video"]["duration_seconds"] == 3600
    assert result["transcript"]["word_count"] == 9
    assert len(result["summary"]["key_insights"]) == 5
    assert result["summary"]["tone"] == "academic"
    assert result["metadata"]["model"]  # actual model name, not stub
    assert result["metadata"]["tokens_used"] > 0
    assert result["metadata"]["cache_hit"] is False
