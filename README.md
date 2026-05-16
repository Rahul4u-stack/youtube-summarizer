# YouTube Video Summarizer

Paste a YouTube link, get a structured summary back — key insights, executive summary, action items, topics covered. Built as Week 2 of [Rahul Agarwal's 9-week AI portfolio](https://ai-portfolio-seven-drab.vercel.app/).

## Status

- **Phase 1 (2026-05-16):** Flask skeleton + Pydantic schema + 17 tests · DONE
- **Phase 2 (2026-05-16):** Real pipeline live — `yt-dlp` → Whisper.cpp → Claude with prompt caching · DONE
- **Phase 3 (next):** React frontend
- **Phase 4–6:** Integration + deployment + case study

### Phase 2 verified metrics

| Test | Duration | Pipeline time | Tokens | Cache hit |
|------|----------|---------------|--------|-----------|
| "Me at the zoo" (1st YT video ever) | 19s | 17.2s | 651 | n/a (too short for cache) |
| Steve Jobs Stanford 2005 — call 1 | 904s (15 min) | 59.3s | 3731 | False (cache create) |
| Steve Jobs Stanford 2005 — call 2 | 904s (15 min) | 61.6s | 3735 | **True** (~90% cheaper) |

**Cache caveat:** Anthropic only caches content blocks ≥1024 tokens. Short transcripts (under ~5 min of speech) won't trigger the cache, even with `cache_control: ephemeral`. This is a real production constraint worth knowing.

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

## Local dev (backend)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env       # fill in ANTHROPIC_API_KEY

# run tests
pytest -v

# boot server in TEST_MODE (default — returns stubbed payload, no API calls)
python app.py

# boot server in LIVE mode (real pipeline)
TEST_MODE=false python app.py
# -> http://localhost:5001/health
```

### System dependencies (live mode)

- **ffmpeg** — used by `yt-dlp` to extract WAV (`brew install ffmpeg`)
- **whisper.cpp** — local transcription (`brew install whisper-cpp`)
- **Whisper model** — `ggml-small.en.bin`. Default path: `~/.cache/hyperframes/whisper/models/ggml-small.en.bin`. Override via `WHISPER_MODEL` env var if your model lives elsewhere.

In TEST_MODE (default in `.env.example`), `POST /api/summarize` returns a fully-shaped stub without calling any external APIs — great for frontend dev and CI.

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
