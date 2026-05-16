# YouTube Video Summarizer

Paste a YouTube link, get a structured summary back — key insights, executive summary, action items, topics covered. Built as Week 2 of [Rahul Agarwal's 9-week AI portfolio](https://ai-portfolio-seven-drab.vercel.app/).

## Status

**Phase 1 (May 19, 2026):** Backend skeleton — Flask app boots, validates input, returns stubbed `SummaryPayload` in `TEST_MODE`.

**Phase 2 (upcoming):** Wire the real pipeline — `yt-dlp` audio download → Whisper.cpp transcription → Claude API with prompt caching → structured JSON response.

## Architecture

```
React + Vite (Vercel)
      │  POST /api/summarize {url}
      ▼
Flask (Render)
      ├─ yt-dlp        download audio from YouTube
      ├─ Whisper.cpp   audio -> transcript (word-level timestamps)
      ├─ Claude API    transcript -> structured JSON (with prompt caching)
      └─ Pydantic      validate response before returning
```

## Local dev (backend only — Phase 1)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env       # fill in ANTHROPIC_API_KEY when ready

# run tests
pytest -v

# boot server
python app.py
# -> http://localhost:5001/health
```

In TEST_MODE (default in `.env.example`), `POST /api/summarize` returns a stub payload without calling any external APIs — great for frontend dev and CI.

## API

### `GET /health`
```json
{"status": "healthy", "test_mode": true, "model": "claude-sonnet-4-6"}
```

### `POST /api/summarize`
**Request:**
```json
{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}
```

**Response (200):**
```json
{
  "video": {"title": "...", "channel": "...", "duration_seconds": 1234, "url": "..."},
  "transcript": {"full_text": "...", "word_count": 2345, "language": "en"},
  "summary": {
    "executive_summary": "...",
    "key_insights": ["...", "...", "..."],
    "action_items": ["..."],
    "topics_covered": ["..."],
    "tone": "technical"
  },
  "metadata": {
    "generated_at": "2026-05-19T...",
    "model": "claude-sonnet-4-6",
    "tokens_used": 15234,
    "cache_hit": false,
    "pipeline_seconds": 32.4
  }
}
```

**Errors:**
- `400` invalid request body or non-YouTube URL
- `501` live mode requested but pipeline not implemented yet (Phase 1)
- `502` AI returned malformed data (Phase 2)
- `500` unexpected server error

## Tech

- **Backend:** Python 3.9+ · Flask 3 · Anthropic SDK · yt-dlp · Pydantic · gunicorn
- **Frontend (Phase 3):** React 18 · Vite · Tailwind CSS · axios
- **AI:** Claude Sonnet 4.6 (summarization) · Whisper.cpp small.en (transcription, local)
- **Deploy:** Vercel (frontend) · Render (backend)
- **CI:** GitHub Actions (pytest + Vitest on every push)

## Repo

- Live: _coming after Phase 5_
- Case study: [Project Plans/Week-2_YouTube-Summarizer.pdf](../AI%20Plans/Project%20Plans/Week-2_YouTube-Summarizer.pdf)
