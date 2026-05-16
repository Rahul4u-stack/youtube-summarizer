// localStorage-backed list of the last 10 summarized URLs.

const KEY = 'yts:history:v1';
const MAX = 10;

export function getHistory() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Add or move an entry to the top of history. Deduplicates by URL.
 * Each entry: { url, title, channel, duration, addedAt }
 */
export function addToHistory(entry) {
  if (!entry || !entry.url) return getHistory();
  const existing = getHistory().filter((e) => e.url !== entry.url);
  const next = [{ ...entry, addedAt: Date.now() }, ...existing].slice(0, MAX);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* localStorage may be disabled — degrade gracefully */
  }
  return next;
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
  return [];
}
