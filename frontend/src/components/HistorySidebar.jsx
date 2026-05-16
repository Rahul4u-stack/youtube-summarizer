import { useState } from 'react';
import { formatDuration } from '../validation';

export default function HistorySidebar({ items, onPick, onClear }) {
  const [open, setOpen] = useState(true);

  if (!items || items.length === 0) {
    return (
      <aside className="hidden lg:block w-72 shrink-0 p-5 border-r border-slate-800">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Recent</h2>
        <p className="mt-3 text-sm text-slate-500">
          Your last 10 summaries will appear here.
        </p>
      </aside>
    );
  }

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-72 shrink-0 border-r border-slate-800 max-h-screen overflow-y-auto">
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Recent</h2>
            <button
              onClick={onClear}
              className="text-xs text-slate-500 hover:text-red-400"
              aria-label="Clear history"
            >
              clear
            </button>
          </div>
          <ul className="space-y-2">
            {items.map((item, i) => (
              <li key={item.url}>
                <button
                  onClick={() => onPick(item.url)}
                  className="w-full text-left p-3 rounded-lg bg-secondary border border-slate-800 hover:border-accent transition-colors"
                  title={item.url}
                >
                  <div className="text-sm text-slate-100 font-medium line-clamp-2">
                    {item.title || item.url}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 truncate">
                    {item.channel || '—'}
                    {item.duration > 0 && <span> · {formatDuration(item.duration)}</span>}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* Mobile collapsible */}
      <div className="lg:hidden border-b border-slate-800">
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="w-full px-5 py-3 flex items-center justify-between text-sm text-slate-400 hover:bg-secondary"
        >
          <span>Recent ({items.length})</span>
          <span aria-hidden="true">{open ? '▲' : '▼'}</span>
        </button>
        {open && (
          <ul className="px-5 pb-3 space-y-2">
            {items.map((item) => (
              <li key={item.url}>
                <button
                  onClick={() => onPick(item.url)}
                  className="w-full text-left p-3 rounded-lg bg-secondary border border-slate-800"
                >
                  <div className="text-sm text-slate-100 font-medium line-clamp-2">
                    {item.title || item.url}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 truncate">
                    {item.channel || '—'}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
