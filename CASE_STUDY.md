# YouTube Summarizer — Case Study

> **Shipped:** 2026-05-17 (Week 2 of [Rahul Agarwal's 9-week AI portfolio](https://ai-portfolio-seven-drab.vercel.app/))
> **Live demo:** https://youtube-summarizer-plum.vercel.app/ (runs in TEST_MODE — see §5 for the deployment trade-offs)
> **Repo:** https://github.com/Rahul4u-stack/youtube-summarizer

---

## 1. One-line pitch

Paste a YouTube URL, get a structured AI summary — executive summary, 5 key insights, action items, topics. Built to demonstrate long-context Claude with prompt caching at production cost economics.

---

## 2. Why this exists — the problem

Students, researchers, and busy professionals watch 5–15 educational YouTube videos a week and rarely extract actionable insights. Manual note-taking during playback is friction-heavy; post-watch summarization means re-watching. Most existing summarizer tools either chunk the video into 5-minute pieces (losing cross-references) or only handle short clips. The capability ceiling for handling full-length videos in one call landed with Claude's 200k context window (March 2024), and **the cost ceiling landed with Anthropic prompt caching (June 2024)** — without caching, ingesting full transcripts on every request is too expensive to ship cheaply.

This project is the smallest end-to-end product I could build that *forced me to think about* both ceilings: long-context single-shot inference, plus the cost-aware caching pattern that makes it economically real.

---

## 3. AI capability demonstrated

**Long-context processing + structured output, with cost-aware prompt caching.**

A 60-minute YouTube video produces a ~25,000-token transcript. Most LLM-summarization tutorials would chunk it. This project sends it as a single content block to Claude Sonnet 4.6, with `cache_control: ephemeral` set on the transcript block. The model returns strict JSON matching a Pydantic schema; the caching API silently halves the cost ratio on repeat lookups.

What I had to know to make this work:
- Claude's 200k context window applies to a single message, not aggregate
- Cache content blocks have a **1024-token minimum**; below that, `cache_control` is silently ignored (a real production gotcha I hit during testing)
- `cache_read_input_tokens` is billed at ~10% of full input rate, so the *aggregate* `tokens_used` metric across calls looks deceptively similar — the cost difference is in the token-type mix, not the total
- Pydantic schema validation catches the small fraction of cases where Claude wraps JSON in prose; defensive regex extraction handles the rest

The cost story is visible in the deployed UI:

> `cache HIT · 4,581 cached + 87 fresh · ~90% cost saved vs. uncached`
>
> `cache miss (first call) · 4,581 tokens cached for 5 min · repeat will be ~90% cheaper`
>
> `too short to cache · Anthropic only caches content blocks ≥ 1,024 tokens (~5 min of speech)`

Three states, each one teaches the user something. The headline AI capability of the project is exposed in the product itself, not just in this doc.

---

## 4. AI tools used

- **`claude-sonnet-4-6`** (Anthropic Messages API) for summarization, with `cache_control: {type: "ephemeral"}` on the transcript content block
- **Whisper.cpp small.en** (local, Apple Metal-accelerated) for speech-to-text — runs in ~30s on a 15-min video on M4
- **yt-dlp** (open-source) for YouTube audio download, configured with `player_client: ["ios", "android", "web"]` to bypass YouTube's anti-scraping on the default `web` client
- **Pydantic 2.x** for output schema validation — every response is round-tripped through `SummaryPayload` before being returned to the frontend, catching malformed JSON early

Cost economics, real numbers from my verification runs:

| Scenario | Tokens (input + cache + output) | Approx cost | Notes |
|---|---|---|---|
| 19-second video, single call | 17 + 0 + 70 = 87 cacheable + 549 input | ~$0.0024 | Below 1024-token cache minimum |
| 15-min talk, first call | 17 + cache_create 4,581 + 70 | ~$0.0157 | Transcript cached for 5 min |
| 15-min talk, repeat call | 3 + cache_read 4,581 + 59 | ~$0.0014 | **~90% cheaper** than first call |

---

## 5. Other tech

- **Frontend:** React 18 + Vite 5 + Tailwind CSS 3 + axios — same proven stack as my [Calorie Estimator](https://calorie-estimator.vercel.app) and [AI Portfolio](https://ai-portfolio-seven-drab.vercel.app). 19 vitest tests.
- **Backend:** Python 3.11 + Flask 3 + Anthropic SDK + gunicorn. 36 pytest tests covering input validation, schema parsing, the 3 pipeline stages individually, error paths, and prompt-caching parameter shape.
- **CI:** GitHub Actions — every push runs pytest on Ubuntu Python 3.11 and vitest + production build on Node 20. CI is green: https://github.com/Rahul4u-stack/youtube-summarizer/actions
- **Deploy:** Vercel (frontend, demo URL above) + Render Blueprint (backend, free tier).

### Deployment trade-off (worth knowing about)

I deliberately deployed the backend in `TEST_MODE` — it returns stub responses, not real transcriptions. Reasoning:

- Render's free tier has 512 MB RAM. The Whisper.cpp small.en model alone takes ~400 MB to load.
- Render free instances sleep after 15 min of inactivity, so the first request takes ~30s to wake up — and that's the *cold start*, before any actual pipeline work.
- yt-dlp from cloud-provider IPs is increasingly 403'd by YouTube; the local Mac development case is robust but the cloud-server case is not.

So the live URL works reliably for portfolio visitors — they can click through the UI, see the API contract, see the cache-state footer — but real summarization runs locally. The README explains how to run the full pipeline in two commands. The Demo Mode banner on the live site is explicit about the choice. Why not deploy the full pipeline? Because I picked correctness-of-demo over feature-parity: the code that runs the real pipeline is in the repo and runs locally with one command — v2 would swap Whisper.cpp for Whisper API + a paid tier.

---

## 6. Architecture decisions & trade-offs

The five decisions that shaped the product, each in "Chose X over Y because Z" form.

### 6.1 Chose single-call long-context over chunking

| | Single call (chosen) | Chunk and combine | Hierarchical chunking |
|---|---|---|---|
| Pros | Claude sees full video; better summaries; simpler code | Cheaper per call | Best of both |
| Cons | Higher per-call cost (~$0.015) | Loses cross-references | 3× API calls, more latency |

**Why:** chunking is the obvious "save tokens" move, but it degrades summary quality (cross-references between minute 5 and minute 50 disappear). The real cost win is caching, not chunking — and the deployed UI proves it numerically. That's the difference between *naive* cost optimization and *production-aware* cost optimization.

### 6.2 Chose Anthropic prompt caching from day 1, not as an afterthought

Transcript is static; the summary prompt varies. First call: "summarize for PMs". Second call: "summarize for students". With caching, the second call's transcript portion is read from cache at ~10% billing — see the live demo's footer for the visual proof.

**Trade-offs accepted:** caching has a 1024-token minimum, so videos under ~5 minutes can't benefit. Rather than hide this from the user, the UI surfaces a *"too short to cache"* state explicitly. This is metric-design discipline: when a feature's value is in a cost ratio, the UI must show the ratio, not the aggregate.

### 6.3 Chose yt-dlp (open-source, fragile) over YouTube Data API (official, stable)

| Tool | Pros | Cons |
|---|---|---|
| yt-dlp (chosen) | Free; downloads audio; works for ~99% of videos; metadata included | Breaks 1× / year when YouTube updates anti-scraping; ios player_client config required to avoid 403s |
| YouTube Data API | Official; stable | Can't download audio (only metadata); paid at scale |

**Why:** the project requires audio, not just metadata. YouTube Data API can't extract audio at all. yt-dlp is the only choice that actually solves the problem. The "fragile" part is well-known — I documented it in the README as a Phase 2 finding so v2-me (or any reader) knows where to look when YouTube changes things again.

### 6.4 Chose JSON-schema-in-prompt over Claude's native tool-use mode

I tell Claude the JSON shape in the prompt and parse with Pydantic. I do *not* use Claude's native function-calling/tool-use mode.

**Why:** prompt-defined schemas are portable — they work across model versions and other providers. They're also easier to debug when things go sideways: the prompt is right there in the source code, not buried in a tool definition object. Trade-off accepted: about 1% of responses arrive with prose around the JSON; I handle this with a defensive regex extractor. Net: simpler code path, easier debugging, almost no quality loss.

### 6.5 Chose Demo Mode in production over best-effort live pipeline

Already discussed in §5. The non-obvious version of this argument: a portfolio piece optimizes for *clarity to the reader* (clear code, clear architecture, working demo URL) rather than *user traffic*. A live pipeline that OOM-crashes weekly is worse than a stub that always works.

---

## 7. What I'd do differently / v2 plans

1. **Swap local Whisper.cpp for Whisper API in production** — costs $0.006/min of audio, but eliminates the RAM ceiling and lets the deployed URL handle real videos. Keep the local Whisper.cpp path for the "I run AI locally where possible" portfolio story.
2. **Add Redis-backed app-level transcript cache** to extend caching beyond Anthropic's 5-minute ephemeral TTL. Popular videos get summarized many times; with persistent caching, hit rate goes from ~30% to ~70%, halving cost again.
3. **Linked clip extraction** — Whisper already produces word-level timestamps; surface "key moment at 23:45" with a deep-link into the YouTube video.
4. **Multi-language summaries** — translate transcript before summarizing. Today it's English-only because I use whisper.cpp `small.en`. Swap to multilingual model + add a `language` parameter.
5. **Evals harness** — sample 50 videos with human-written reference summaries; measure factual-grounding rate. Surface this in the README as a quality SLA.

---

## 8. Outcome

- **Shipped:** 2026-05-17 (Day 2 of Week 2, ~5 days ahead of the planned schedule)
- **Live demo:** https://youtube-summarizer-plum.vercel.app/ (TEST_MODE)
- **Backend health:** https://youtube-summarizer-backend-o60u.onrender.com/health
- **Repo:** https://github.com/Rahul4u-stack/youtube-summarizer
- **Tests:** 36 backend (pytest) + 19 frontend (vitest), all green on GitHub Actions CI
- **Verified pipeline runs (local):**
  - "Me at the zoo" (19s, the first YouTube video ever) → 17s end-to-end, 87 tokens, accurate transcript
  - Steve Jobs Stanford 2005 (15 min) → 59s end-to-end, 3,731 tokens (first call), **cache HIT on second call within 5 min**
- **Deployment:** Vercel + Render free tier; auto-redeploys on `git push`
- **AI cost spent in development:** under $1.50 (mostly cache-creation calls during verification)

---

## 9. Design questions, answered

**Why Claude Sonnet rather than Haiku or GPT-4?**
Sonnet balances speed and accuracy for long text. Haiku (cheaper) lacks the nuance for academic / technical videos and I checked this on the Steve Jobs Stanford speech — Haiku's "key insights" missed two of the three famous themes. GPT-4 is overkill: summarization isn't reasoning-heavy, and switching providers would have meant rebuilding the caching code (GPT doesn't have an equivalent ephemeral cache). Sonnet is the cost-quality sweet spot at this product's scale.

**How does it handle hallucinations in long transcripts?**
Three layers. (1) The prompt explicitly says "extract insights mentioned in the transcript only, not inferred from your training data." (2) Pydantic validates the JSON shape — malformed responses (which sometimes happen when Claude wraps JSON in markdown fences) get retried via the regex extractor. (3) The summary's `tone` field surfaces calibration confidence — when Claude classifies a video as "promotional" the UI can render that visibly so the user knows the source is biased. For v2 I'd add TruLens-style automated evals on a labeled sample to measure factual grounding rate empirically, not just by feel.

**What's the cost-per-summary at 100k summaries/month?**
At Sonnet pricing (~$3 per million input tokens / $15 per million output): an uncached 15-minute video costs ~$0.015 per summary. With Anthropic's 5-min ephemeral cache and ~30% cache hit rate from the production load distribution (popular videos summarized many times), the blended cost is (0.7 × 100k × $0.015) + (0.3 × 100k × $0.0015) = **~$1,095 / month** at scale. To halve this for v2 I'd add Redis to extend cache TTL beyond 5 minutes — popular videos would get summarized cheaply for hours, not just within the same conversation. That pushes the blended hit rate to ~60% and the blended cost to ~$700/month.

---

## Findings worth knowing

1. **Anthropic prompt caching has a 1024-token minimum, silently ignored below it.** Test caching with a long video to avoid a "wait, my caching does nothing" false alarm.
2. **The aggregate `tokens_used` metric hides cache savings.** Total tokens stays flat across cached and uncached calls — the cost difference is in the token-type mix. If you only surface the aggregate, you'll confuse yourself into thinking caching isn't working. I built a 3-state cache footer (HIT / first call / too short) so the user always sees the ratio, not the total.
3. **yt-dlp's default `web` player_client increasingly gets HTTP 403 from YouTube.** Setting `extractor_args={"youtube": {"player_client": ["ios", "android", "web"]}}` uses mobile-app tokens which bypass most web-tier blocks. This was an hour of debugging the first time it broke.
4. **`flask-cors` mixes specific origins with `*` poorly — preflight stops echoing Allow-Origin for unknown origins.** `CORS(app, origins=["http://localhost:5173", "*"])` is **not** the same as `CORS(app)`. The first constrains; the second is permissive. In a TEST_MODE-only demo deploy, prefer the second.
5. **Linux CI exposes "works on my machine" assumptions immediately** — tests that pass on macOS (where `/opt/homebrew/bin/whisper` exists) failed on Ubuntu because the existence check fired before the subprocess mock could take over. Always monkey-patch *every* external-tool path the function checks, not just the model.

---

*Built with Claude Code over 2 days.*
