// Accepts youtube.com/watch?v=, youtu.be/, and youtube.com/shorts/ forms.
// 11-char video ID. Matches the same regex used by the backend's
// is_valid_youtube_url() so frontend and backend agree on what's a valid URL.
const YOUTUBE_URL_RE =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)[\w-]{11}/;

export function isValidYoutubeUrl(url) {
  if (typeof url !== 'string') return false;
  return YOUTUBE_URL_RE.test(url.trim());
}

export function formatDuration(seconds) {
  const n = Math.max(0, Math.round(seconds || 0));
  const h = Math.floor(n / 3600);
  const m = Math.floor((n % 3600) / 60);
  const s = n % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}
