"""YouTube Video Summarizer — Flask backend.

Phase 1 (skeleton): wires up the request/response shape, returns a stubbed
summary in TEST_MODE so the frontend and CI can run without real API calls.

Phase 2 will fill in the real pipeline:
    URL -> yt-dlp (audio) -> Whisper (transcript) -> Claude (summary).
"""
import os
import json
import logging
import re
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

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:5173",
    os.getenv("FRONTEND_URL", "*"),
])

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
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

    # Phase 2 will replace this with the real pipeline.
    logger.warning("Live mode requested but pipeline not implemented (Phase 2).")
    return jsonify({
        'error': 'Live pipeline not implemented yet. Set TEST_MODE=true in .env, '
                 'or wait for Phase 2 (yt-dlp + Whisper + Claude integration).',
    }), 501


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') == 'development'
    logger.info("Starting on port %s | TEST_MODE=%s | MODEL=%s", port, TEST_MODE, MODEL)
    app.run(host='0.0.0.0', port=port, debug=debug)
