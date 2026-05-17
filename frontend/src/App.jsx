import { useEffect, useState } from 'react';
import UrlInputForm from './components/UrlInputForm';
import LoadingState from './components/LoadingState';
import ErrorMessage from './components/ErrorMessage';
import SummaryDisplay from './components/SummaryDisplay';
import HistorySidebar from './components/HistorySidebar';
import DemoBanner from './components/DemoBanner';
import { summarize, health, ApiError, apiBase } from './api';
import { getHistory, addToHistory, clearHistory } from './history';

export default function App() {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [coldStart, setColdStart] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [testMode, setTestMode] = useState(null); // null until /health resolves

  // Load history on mount + probe backend mode
  useEffect(() => {
    setHistory(getHistory());
    health().then((h) => {
      if (h.ok) setTestMode(Boolean(h.test_mode));
    });
  }, []);

  const handleSubmit = async (url) => {
    setLoading(true);
    setColdStart(false);
    setError(null);
    setPayload(null);
    try {
      const data = await summarize(url, {
        onColdStartHint: () => setColdStart(true),
      });
      setPayload(data);
      const updated = addToHistory({
        url,
        title: data?.video?.title,
        channel: data?.video?.channel,
        duration: data?.video?.duration_seconds,
      });
      setHistory(updated);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      } else {
        setError(new ApiError(err.message || 'Unexpected error', {}));
      }
    } finally {
      setLoading(false);
      setColdStart(false);
    }
  };

  const handleClearHistory = () => {
    clearHistory();
    setHistory([]);
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      <HistorySidebar
        items={history}
        onPick={handleSubmit}
        onClear={handleClearHistory}
      />

      <main className="flex-1 px-5 py-10 lg:py-16">
        <DemoBanner show={testMode === true} />

        <header className="max-w-2xl mx-auto text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            YouTube <span className="text-accent">Summarizer</span>
          </h1>
          <p className="mt-3 text-slate-400">
            Paste a YouTube link, get a structured AI summary — key insights,
            action items, and the full transcript. Powered by Claude + Whisper.
          </p>
        </header>

        <UrlInputForm onSubmit={handleSubmit} loading={loading} />

        {loading && <LoadingState coldStart={coldStart} />}
        <ErrorMessage error={error} onDismiss={() => setError(null)} />
        {payload && !loading && <SummaryDisplay payload={payload} />}

        <footer className="mt-16 text-center text-xs text-slate-500">
          <p>
            API: <span className="font-mono">{apiBase}</span>
          </p>
          <p className="mt-1">
            Week 2 of <a href="https://github.com/Rahul4u-stack" className="text-accent hover:text-accent-hover">Rahul Agarwal's AI portfolio</a>
          </p>
        </footer>
      </main>
    </div>
  );
}
