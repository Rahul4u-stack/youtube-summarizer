import { useState } from 'react';
import { formatDuration } from '../validation';

export default function SummaryDisplay({ payload }) {
  const [showTranscript, setShowTranscript] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!payload) return null;
  const { video, transcript, summary, metadata } = payload;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard might not be available */
    }
  };

  return (
    <article className="w-full max-w-3xl mx-auto mt-8 space-y-6">
      {/* Video header */}
      <header className="rounded-xl bg-secondary border border-slate-700 overflow-hidden">
        <div className="flex flex-col sm:flex-row">
          {video?.thumbnail_url && (
            <img
              src={video.thumbnail_url}
              alt=""
              className="w-full sm:w-48 h-auto sm:h-32 object-cover bg-slate-800"
            />
          )}
          <div className="flex-1 p-5">
            <h2 className="text-xl font-semibold text-slate-50 leading-tight">
              {video?.title || 'Untitled video'}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              <span>{video?.channel || 'Unknown channel'}</span>
              {video?.duration_seconds > 0 && (
                <>
                  <span className="mx-2">·</span>
                  <span>{formatDuration(video.duration_seconds)}</span>
                </>
              )}
              {transcript?.word_count > 0 && (
                <>
                  <span className="mx-2">·</span>
                  <span>{transcript.word_count.toLocaleString()} words</span>
                </>
              )}
            </p>
            {video?.url && (
              <a
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-2 text-sm text-accent hover:text-accent-hover"
              >
                Open on YouTube ↗
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Executive summary */}
      {summary?.executive_summary && (
        <Section title="Executive Summary">
          <p className="text-slate-200 leading-relaxed whitespace-pre-line">
            {summary.executive_summary}
          </p>
        </Section>
      )}

      {/* Key insights */}
      {summary?.key_insights?.length > 0 && (
        <Section title="Key Insights">
          <ul className="space-y-2">
            {summary.key_insights.map((insight, i) => (
              <li key={i} className="flex gap-3 text-slate-200">
                <span className="text-accent font-bold mt-0.5">{i + 1}.</span>
                <span className="flex-1">{insight}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Action items */}
      {summary?.action_items?.length > 0 && (
        <Section title="Action Items">
          <ul className="space-y-2">
            {summary.action_items.map((item, i) => (
              <li key={i} className="flex gap-3 text-slate-200">
                <span className="text-emerald-400 mt-0.5" aria-hidden="true">☐</span>
                <span className="flex-1">{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Topics */}
      {summary?.topics_covered?.length > 0 && (
        <Section title="Topics">
          <div className="flex flex-wrap gap-2">
            {summary.topics_covered.map((topic, i) => (
              <span
                key={i}
                className="px-3 py-1 text-xs rounded-full bg-slate-800 text-slate-300 border border-slate-700"
              >
                {topic}
              </span>
            ))}
            {summary.tone && (
              <span className="px-3 py-1 text-xs rounded-full bg-accent/20 text-accent border border-accent/40">
                tone: {summary.tone}
              </span>
            )}
          </div>
        </Section>
      )}

      {/* Transcript (collapsible) */}
      {transcript?.full_text && (
        <Section title="Transcript">
          <button
            onClick={() => setShowTranscript((v) => !v)}
            aria-expanded={showTranscript}
            className="text-sm text-accent hover:text-accent-hover"
          >
            {showTranscript ? 'Hide' : 'Show'} full transcript ({transcript.word_count?.toLocaleString() || '?'} words)
          </button>
          {showTranscript && (
            <p className="mt-3 text-sm text-slate-300 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto p-4 rounded bg-primary border border-slate-800 font-mono">
              {transcript.full_text}
            </p>
          )}
        </Section>
      )}

      {/* Metadata + copy JSON */}
      <footer className="rounded-xl bg-secondary/60 border border-slate-800 p-4 space-y-3 text-xs text-slate-400">
        <CacheStatus metadata={metadata} />
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <span>model: <span className="text-slate-300 font-mono">{metadata?.model}</span></span>
            <span>tokens: <span className="text-slate-300 font-mono">{metadata?.tokens_used?.toLocaleString() || 0}</span></span>
            {metadata?.pipeline_seconds > 0 && (
              <span>elapsed: <span className="text-slate-300 font-mono">{metadata.pipeline_seconds.toFixed(1)}s</span></span>
            )}
          </div>
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 rounded text-sm bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 self-start sm:self-auto"
          >
            {copied ? '✓ Copied' : 'Copy JSON'}
          </button>
        </div>
      </footer>
    </article>
  );
}

/**
 * Render one of three cache states based on the metadata token breakdown:
 *   1. HIT       — cache_read_tokens > 0   →  show savings ratio
 *   2. MISS first call — cache_creation_tokens > 0  →  cached for next 5 min
 *   3. Too short — neither — content was below Anthropic's 1024-token minimum
 * The stub backend response has all-zeroes for the breakdown, which renders
 * as state #3 with a "demo response" hint instead.
 */
function CacheStatus({ metadata }) {
  if (!metadata) return null;

  const cacheRead = metadata.cache_read_tokens || 0;
  const cacheCreate = metadata.cache_creation_tokens || 0;
  const input = metadata.input_tokens || 0;
  const output = metadata.output_tokens || 0;
  const isStub = metadata.model === 'stub';

  // Bills approximation: cache_read ≈ 10% of input rate, cache_create ≈ 125%
  // of input rate. (Output is billed separately and roughly same across calls.)
  // We compare "what it would have cost without caching" vs "what it cost now".
  const fresh = input + cacheCreate;
  const totalCached = cacheRead;
  const savingsPct = totalCached > 0
    ? Math.round((1 - 0.1) * 100 * totalCached / (totalCached + fresh))
    : 0;

  if (metadata.cache_hit && cacheRead > 0) {
    return (
      <div className="flex items-center gap-2 text-emerald-400 font-medium">
        <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" aria-hidden="true" />
        <span>
          cache HIT · {cacheRead.toLocaleString()} cached + {fresh.toLocaleString()} fresh ·
          <span className="text-emerald-300"> ~{savingsPct}% cost saved vs. uncached</span>
        </span>
      </div>
    );
  }

  if (cacheCreate > 0) {
    return (
      <div className="flex items-center gap-2 text-sky-300 font-medium">
        <span className="inline-block w-2 h-2 rounded-full bg-sky-400" aria-hidden="true" />
        <span>
          cache miss (first call) · {cacheCreate.toLocaleString()} tokens cached for 5 min ·
          <span className="text-sky-200"> repeat will be ~90% cheaper</span>
        </span>
      </div>
    );
  }

  if (isStub) {
    return (
      <div className="flex items-center gap-2 text-amber-300 font-medium">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-400" aria-hidden="true" />
        <span>demo response · token breakdown not applicable in TEST_MODE</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-slate-400 font-medium">
      <span className="inline-block w-2 h-2 rounded-full bg-slate-500" aria-hidden="true" />
      <span>
        too short to cache · Anthropic only caches content blocks ≥ 1,024 tokens
        (~5 min of speech)
      </span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="rounded-xl bg-secondary border border-slate-700 p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400 mb-3">
        {title}
      </h3>
      {children}
    </section>
  );
}
