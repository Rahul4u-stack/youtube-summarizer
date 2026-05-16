"""Phase 1 smoke tests.

These verify the skeleton boots correctly and the API contract is enforced.
Phase 2 will add tests for the yt-dlp/Whisper/Claude pipeline.
"""
import json

import pytest

from app import app, is_valid_youtube_url


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
