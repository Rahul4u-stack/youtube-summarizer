// Thin wrapper around the backend /api/summarize endpoint.
// Handles: timeout (long), abort, JSON parsing, cold-start detection.

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

// 4 minutes — Whisper on a 15-min video runs ~60s, plus yt-dlp + Claude.
const REQUEST_TIMEOUT_MS = 240_000;

export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * POST /api/summarize { url }
 * Returns the parsed SummaryPayload on success.
 * Throws ApiError on backend errors, TimeoutError on timeout.
 */
export async function summarize(url, { onColdStartHint } = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  // After 8s with no response, hint to the user that Render may be cold-starting
  let coldStartTimer = null;
  if (onColdStartHint) {
    coldStartTimer = setTimeout(() => onColdStartHint(), 8000);
  }

  try {
    const response = await fetch(`${API_URL}/api/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal: controller.signal,
    });

    let body;
    try {
      body = await response.json();
    } catch {
      body = {};
    }

    if (!response.ok) {
      throw new ApiError(body.error || `Request failed (${response.status})`, {
        status: response.status,
        detail: body.detail,
      });
    }
    return body;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new ApiError(
        'The server took too long to respond. Try a shorter video, or wait and retry.',
        { status: 408 },
      );
    }
    if (err.name === 'TypeError' && /fetch/i.test(err.message)) {
      throw new ApiError(
        `Cannot reach the backend at ${API_URL}. Make sure it's running.`,
        { status: 0 },
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
    if (coldStartTimer) clearTimeout(coldStartTimer);
  }
}

export async function health() {
  try {
    const response = await fetch(`${API_URL}/health`, { method: 'GET' });
    if (!response.ok) return { ok: false };
    return { ok: true, ...(await response.json()) };
  } catch {
    return { ok: false };
  }
}

export const apiBase = API_URL;
