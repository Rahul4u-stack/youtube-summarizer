"""YouTube Video Summarizer — Flask backend.

Phase 2: full pipeline.
  POST /api/summarize {url}
    -> yt-dlp downloads audio + metadata
    -> Whisper.cpp transcribes
    -> Claude summarizes with prompt caching
    -> Pydantic-validated JSON response

TEST_MODE=true short-circuits to a stub so frontend dev & CI don't need
API credits.
"""
import os
import logging
import re
import tempfile
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from models import (
    SummarizeRequest,
    SummaryPayload,
    VideoMetadata,
    TranscriptInfo,
    SummaryContent,
    ResponseMetadata,
)
from pipeline import (
    run_pipeline,
    DownloadError,
    TranscribeError,
    SummarizeError,
)

load_dotenv()
# Some shells (certain IDE / agent environments) export ANTHROPIC_API_KEY=""
# which prevents the .env value from being used (load_dotenv() doesn't
# override "set" vars, even when their value is the empty string). Treat
# empty-string env vars as missing and refill from .env. Real non-empty
# shell vars (e.g. TEST_MODE=false passed on the command line) win.
from dotenv import dotenv_values
for _k, _v in dotenv_values().items():
    if _v and not os.environ.get(_k):
        os.environ[_k] = _v

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

app = Flask(__name__)
# In TEST_MODE the API only returns stub payloads, so allow any origin —
# this lets the demo work from any preview deploy without dashboard fiddling.
# In live mode, lock CORS down to known frontends (localhost + FRONTEND_URL).
# Note: flask-cors mixes specific origins with "*" poorly (preflight stops
# echoing Allow-Origin for unknown origins), so we pick one mode or the other.
if TEST_MODE:
    CORS(app)
else:
    _live_origins = ["http://localhost:3000", "http://localhost:5173"]
    _frontend_url = os.getenv("FRONTEND_URL")
    if _frontend_url:
        _live_origins.append(_frontend_url)
    CORS(app, origins=_live_origins)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Accepted YouTube URL forms:
#   https://www.youtube.com/watch?v=VIDEO_ID
#   https://youtu.be/VIDEO_ID
#   https://youtube.com/shorts/VIDEO_ID
YOUTUBE_URL_RE = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]{11}'
)


def is_valid_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_URL_RE.match(url.strip()))


def stub_summary_payload(url: str) -> dict:
    """Return a placeholder payload for TEST_MODE and Phase 1 verification."""
    payload = SummaryPayload(
        video=VideoMetadata(
            title="Sample YouTube Video (TEST MODE)",
            channel="Sample Channel",
            duration_seconds=600,
            url=url,
            thumbnail_url=None,
        ),
        transcript=TranscriptInfo(
            full_text="This is a stubbed transcript returned in TEST_MODE. "
                      "Set TEST_MODE=false in .env and implement the real "
                      "pipeline in Phase 2 to get actual results.",
            word_count=28,
            language="en",
        ),
        summary=SummaryContent(
            executive_summary=(
                "TEST MODE response. The real pipeline (yt-dlp -> Whisper -> "
                "Claude) is implemented in Phase 2. This stub proves the API "
                "contract works end-to-end."
            ),
            key_insights=[
                "Phase 1 ships a skeleton, not the real pipeline.",
                "TEST_MODE lets the frontend develop without API credits.",
                "Pydantic validates every response before it leaves the server.",
            ],
            action_items=[
                "Implement yt-dlp audio download in Phase 2.",
                "Wire Whisper.cpp transcription in Phase 2.",
                "Add Claude prompt caching in Phase 2.",
            ],
            topics_covered=["test mode", "skeleton", "phase 1"],
            tone="technical",
        ),
        metadata=ResponseMetadata(
            generated_at=datetime.now(timezone.utc).isoformat(),
            model="stub",
            tokens_used=0,
            cache_hit=False,
            pipeline_seconds=0.0,
            input_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            output_tokens=0,
        ),
    )
    return payload.model_dump()


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'test_mode': TEST_MODE, 'model': MODEL})


@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'name': 'YouTube Summarizer API',
        'status': 'ok',
        'endpoints': {
            'health': 'GET /health',
            'summarize': 'POST /api/summarize  body: {"url": "https://..."}',
        },
    })


@app.route('/api/summarize', methods=['POST'])
def summarize():
    body = request.get_json(silent=True) or {}

    try:
        req = SummarizeRequest(**body)
    except ValidationError as e:
        logger.info("Invalid request body: %s", e.errors())
        return jsonify({'error': 'Invalid request body. Expected JSON: {"url": "..."}'}), 400

    if not is_valid_youtube_url(req.url):
        return jsonify({'error': 'That URL does not look like a YouTube link.'}), 400

    if TEST_MODE:
        logger.info("TEST_MODE: returning stub for url=%s", req.url)
        return jsonify(stub_summary_payload(req.url))

    # Real pipeline (Phase 2)
    logger.info("Pipeline START url=%s", req.url)
    try:
        with tempfile.TemporaryDirectory(prefix="yts_") as tmp:
            payload = run_pipeline(req.url, out_dir=tmp, client=client)
        return jsonify(payload)
    except DownloadError as e:
        logger.warning("Download failed: %s", e)
        return jsonify({
            'error': 'Could not extract audio from this video. '
                     'It may be private, region-locked, or YouTube changed its system. '
                     'Try a different video.',
            'detail': str(e),
        }), 502
    except TranscribeError as e:
        logger.error("Transcription failed: %s", e)
        return jsonify({
            'error': 'Could not transcribe the audio. The video may be too short or silent.',
            'detail': str(e),
        }), 502
    except SummarizeError as e:
        logger.error("Summarization failed: %s", e)
        msg = str(e)
        status = 402 if 'credit' in msg.lower() else 502
        return jsonify({'error': msg}), status
    except Exception as e:
        logger.exception("Unexpected pipeline error")
        return jsonify({'error': 'Unexpected server error. Please try again.'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') == 'development'
    logger.info("Starting on port %s | TEST_MODE=%s | MODEL=%s", port, TEST_MODE, MODEL)
    app.run(host='0.0.0.0', port=port, debug=debug)
