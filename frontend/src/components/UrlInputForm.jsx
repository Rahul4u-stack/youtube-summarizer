import { useState } from 'react';
import { isValidYoutubeUrl } from '../validation';

export default function UrlInputForm({ onSubmit, loading }) {
  const [url, setUrl] = useState('');
  const trimmed = url.trim();
  const valid = isValidYoutubeUrl(trimmed);
  const showHint = trimmed.length > 0 && !valid;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!valid || loading) return;
    onSubmit(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto" aria-label="Summarize a video">
      <label htmlFor="yt-url" className="block text-sm font-medium text-slate-300 mb-2">
        YouTube URL
      </label>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          id="yt-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=…"
          disabled={loading}
          className="flex-1 px-4 py-3 rounded-lg bg-secondary border border-slate-700 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-60"
          autoFocus
          spellCheck={false}
        />
        <button
          type="submit"
          disabled={!valid || loading}
          aria-busy={loading}
          className="px-6 py-3 rounded-lg bg-accent text-white font-medium hover:bg-accent-hover disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {loading ? 'Summarizing…' : 'Summarize'}
        </button>
      </div>
      <div className="mt-2 min-h-[1.25rem] text-xs">
        {showHint && (
          <span className="text-amber-400">
            That doesn't look like a YouTube link. Try `https://www.youtube.com/watch?v=…` or a youtu.be short link.
          </span>
        )}
      </div>
    </form>
  );
}
