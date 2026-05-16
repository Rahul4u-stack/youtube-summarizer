"""Endpoint-level tests.

URL validation, request shape, and the TEST_MODE happy path. Live-mode tests
(TEST_MODE=false) mock run_pipeline. The pipeline functions themselves are
tested in test_pipeline.py.
"""
import json
from unittest.mock import patch

import pytest

import app as app_module
from app import app, is_valid_youtube_url
from pipeline import DownloadError, TranscribeError, SummarizeError


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client


# ---------- Health & root ----------

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body['status'] == 'healthy'
    assert 'test_mode' in body
    assert 'model' in body


def test_root_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body['name'] == 'YouTube Summarizer API'
    assert 'endpoints' in body


# ---------- URL validation ----------

@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://youtube.com/shorts/dQw4w9WgXcQ",
])
def test_valid_youtube_urls(url):
    assert is_valid_youtube_url(url) is True


@pytest.mark.parametrize("url", [
    "",
    "not a url",
    "https://vimeo.com/12345",
    "https://www.youtube.com/",
    "https://youtube.com/watch?v=tooshort",
    "https://example.com/watch?v=dQw4w9WgXcQ",
])
def test_invalid_youtube_urls(url):
    assert is_valid_youtube_url(url) is False


# ---------- /api/summarize input validation ----------

def test_summarize_rejects_missing_body(client):
    response = client.post('/api/summarize')
    assert response.status_code == 400
    assert 'error' in json.loads(response.data)


def test_summarize_rejects_missing_url(client):
    response = client.post('/api/summarize', json={'language': 'en'})
    assert response.status_code == 400


def test_summarize_rejects_invalid_url(client):
    response = client.post('/api/summarize', json={'url': 'https://vimeo.com/12345'})
    assert response.status_code == 400
    body = json.loads(response.data)
    assert 'YouTube' in body['error']


# ---------- /api/summarize TEST_MODE happy path ----------

def test_summarize_returns_stub_in_test_mode(client):
    """conftest sets TEST_MODE=true, so we should get the stub payload."""
    response = client.post('/api/summarize', json={
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    })
    assert response.status_code == 200
    body = json.loads(response.data)

    # Verify the full SummaryPayload contract
    assert 'video' in body
    assert 'transcript' in body
    assert 'summary' in body
    assert 'metadata' in body

    assert body['video']['url'] == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    assert body['video']['duration_seconds'] >= 0
    assert isinstance(body['summary']['key_insights'], list)
    assert isinstance(body['summary']['action_items'], list)
    assert body['metadata']['model'] == 'stub'


# ---------- /api/summarize live-mode (TEST_MODE=false) ----------

@pytest.fixture
def live_mode(monkeypatch):
    """Flip TEST_MODE off for one test so the pipeline path runs."""
    monkeypatch.setattr(app_module, "TEST_MODE", False)


def test_summarize_live_mode_calls_pipeline(client, live_mode):
    fake_payload = {
        "video": {"title": "T", "channel": "C", "duration_seconds": 10, "url": "u", "thumbnail_url": None},
        "transcript": {"full_text": "hello", "word_count": 1, "language": "en"},
        "summary": {
            "executive_summary": "s", "key_insights": ["a"],
            "action_items": [], "topics_covered": ["x", "y", "z"], "tone": "casual",
        },
        "metadata": {
            "generated_at": "2026-05-16T00:00:00+00:00",
            "model": "claude-sonnet-4-6", "tokens_used": 1234,
            "cache_hit": False, "pipeline_seconds": 42.0,
        },
    }
    with patch.object(app_module, "run_pipeline", return_value=fake_payload):
        response = client.post('/api/summarize', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        })
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body["metadata"]["model"] == "claude-sonnet-4-6"
    assert body["metadata"]["tokens_used"] == 1234


def test_summarize_live_mode_download_error_returns_502(client, live_mode):
    with patch.object(app_module, "run_pipeline", side_effect=DownloadError("video unavailable")):
        response = client.post('/api/summarize', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        })
    assert response.status_code == 502
    body = json.loads(response.data)
    assert 'extract audio' in body['error'].lower()


def test_summarize_live_mode_transcribe_error_returns_502(client, live_mode):
    with patch.object(app_module, "run_pipeline", side_effect=TranscribeError("silent audio")):
        response = client.post('/api/summarize', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        })
    assert response.status_code == 502


def test_summarize_live_mode_credit_error_returns_402(client, live_mode):
    with patch.object(app_module, "run_pipeline", side_effect=SummarizeError("credit balance is too low")):
        response = client.post('/api/summarize', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        })
    assert response.status_code == 402


def test_summarize_live_mode_unexpected_error_returns_500(client, live_mode):
    with patch.object(app_module, "run_pipeline", side_effect=RuntimeError("boom")):
        response = client.post('/api/summarize', json={
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        })
    assert response.status_code == 500
