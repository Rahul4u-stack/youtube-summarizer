# YouTube Video Summarizer

> Paste a YouTube URL, get a structured AI summary — executive summary, key insights, action items, topics. Built as Week 2 of [Rahul Agarwal's 9-week AI portfolio](https://ai-portfolio-seven-drab.vercel.app/).

**Live demo:** https://youtube-summarizer-plum.vercel.app/ (runs in TEST_MODE — see below)
**Backend health:** https://youtube-summarizer-backend-o60u.onrender.com/health
**Recruiter case study:** [CASE_STUDY.md](./CASE_STUDY.md)
**Build plan PDF (PM-friendly):** [Week-2_YouTube-Summarizer.pdf](../AI%20Plans/Project%20Plans/Week-2_YouTube-Summarizer.pdf)

---

## What it demonstrates

| AI capability | Visible in the product |
|---|---|
| **Long-context single-call inference** (~25k-token transcripts handled in one Claude call, not chunked) | The summary card renders insights that reference both minute 5 and minute 50 of long videos — chunking would lose that |
| **Anthropic prompt caching** (`cache_control: ephemeral`) | The metadata footer shows one of three cache states: `cache HIT · X cached + Y fresh · ~90% saved` / `cache miss (first call) · cached for next 5 min` / `too short to cache (<1,024 tokens)` |
| **Structured output via Pydantic** | Every response is round-tripped through `SummaryPayload` — malformed JSON is caught at the server boundary |
| **Graceful failure handling** | yt-dlp 403s, Whisper timeouts, Claude credit exhaustion all map to distinct HTTP status codes with friendly UI messages |

## Why the live demo runs in TEST_MODE

The deployed backend returns stub responses, not real transcriptions. **By design.**

- Render's free tier has 512 MB RAM; the Whisper.cpp small.en model needs ~400 MB just to load
- Render instances sleep after 15 min, so cold-start latency would dominate user experience
- yt-dlp from cloud-provider IPs is increasingly 403'd by YouTube

The full pipeline runs locally with one command (see [Local dev](#local-dev-backend) below). The deployed code is identical to the local pipeline — only the `TEST_MODE=true` env var on Render differs. Demo-mode banner on the live site is explicit about the choice. v2 would swap Whisper.cpp for Whisper API on a paid tier; the trade-off is explained in [§5 of the case study](./CASE_STUDY.md#5-other-tech-full-stack-signal).

## Build timeline

| Phase | Date | What shipped |
|---|---|---|
| 1 | 2026-05-16 | Flask skeleton + Pydantic schema + 17 pytest tests |
| 2 | 2026-05-16 | Real pipeline: yt-dlp → Whisper.cpp → Claude with prompt caching |
| 3 | 2026-05-16 | React + Vite + Tailwind frontend, 19 vitest tests |
| 4 | 2026-05-17 | GitHub Actions CI (green on every push) |
| 5 | 2026-05-17 | Deployed to Vercel + Render, demo banner, project card on portfolio |
| 6 | 2026-05-17 | CASE_STUDY.md + 3-state cache footer surfacing the cost-savings story in the UI |

Each phase's "How to verify in Terminal" instructions and "Interesting Findings & Blockers" log are in the plan PDF linked above — 6 phases × 1 finding-per-phase minimum.

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

In production both Vercel and Render are on the free tier. The frontend stays warm always; the backend sleeps after 15 min of inactivity and takes ~30s to wake up (handled gracefully by the frontend with a "warming up" message).

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

### System dependencies (live mode only)

- **ffmpeg** — used by `yt-dlp` to extract WAV (`brew install ffmpeg`)
- **whisper.cpp** — local transcription (`brew install whisper-cpp`)
- **Whisper model** — `ggml-small.en.bin`. Default path: `~/.cache/hyperframes/whisper/models/ggml-small.en.bin`. Override via `WHISPER_MODEL` env var if your model lives elsewhere.

In TEST_MODE (default in `.env.example`), `POST /api/summarize` returns a fully-shaped stub without calling any external APIs — great for frontend dev and CI.

## Local dev (frontend)

```bash
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

The frontend reads `VITE_API_URL` from `.env.local`; default is `http://localhost:5001`. Tests run via `npm test`.

## Production deployment

### Render (backend)

1. From the Render dashboard → **New +** → **Blueprint**
2. Connect this GitHub repo. Render reads `render.yaml` and creates a `youtube-summarizer-backend` web service.
3. In the service's **Environment** tab, set the secrets:
   - `ANTHROPIC_API_KEY` — your key from console.anthropic.com
   - `FRONTEND_URL` — your Vercel URL once known (for CORS)
4. Deploy. Health URL: `https://<your-name>.onrender.com/health`

Free tier note: the instance sleeps after 15&nbsp;min of inactivity. First request after sleep takes ~30s to wake — the frontend shows a "warming up" hint after 8s.

### Vercel (frontend)

1. From the Vercel dashboard → **Add New** → **Project**
2. Import this GitHub repo
3. **Root Directory:** `frontend`
4. Framework preset: **Vite** (auto-detected)
5. Add environment variable:
   - `VITE_API_URL` = your Render backend URL (e.g., `https://youtube-summarizer.onrender.com`)
6. Deploy. The site will be at `https://<vercel-auto-name>.vercel.app`.

After both are live, update the Render service's `FRONTEND_URL` to the Vercel URL and redeploy so CORS allows it.

## Phase 2 verified metrics (local)

| Test | Duration | Pipeline time | Tokens | Cache hit |
|------|----------|---------------|--------|-----------|
| "Me at the zoo" (1st YT video ever) | 19s | 17.2s | 651 | n/a (too short for cache) |
| Steve Jobs Stanford 2005 — call 1 | 904s (15 min) | 59.3s | 3731 | False (cache create) |
| Steve Jobs Stanford 2005 — call 2 | 904s (15 min) | 61.6s | 3735 | **True** (~90% cheaper) |

**Cache caveat:** Anthropic only caches content blocks ≥1024 tokens. Short transcripts (under ~5 min of speech) won't trigger the cache, even with `cache_control: ephemeral`. This is a real production constraint worth knowing.

## API

### `GET /health`
```json
{"status": "healthy", "test_mode": true, "model": "claude-sonnet-4-6"}
```
The frontend uses this to render the "Demo mode" banner when `test_mode` is true.

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
- `402` Anthropic credits exhausted
- `408` request took too long (>4 min)
- `501` live mode requested but Whisper not installed
- `502` AI returned malformed data, or yt-dlp/Whisper failed
- `500` unexpected server error

## Tech

- **Backend:** Python 3.11 · Flask 3 · Anthropic SDK · yt-dlp · Pydantic · gunicorn
- **Frontend:** React 18 · Vite · Tailwind CSS · axios
- **AI:** Claude Sonnet 4.6 (summarization with prompt caching) · Whisper.cpp small.en (local transcription)
- **Deploy:** Vercel (frontend) · Render (backend)
- **CI:** GitHub Actions (pytest 36 + vitest 19 + frontend build on every push)

## Repo

- Repo: https://github.com/Rahul4u-stack/youtube-summarizer
- Case study: [Week-2_YouTube-Summarizer.pdf](../AI%20Plans/Project%20Plans/Week-2_YouTube-Summarizer.pdf)
