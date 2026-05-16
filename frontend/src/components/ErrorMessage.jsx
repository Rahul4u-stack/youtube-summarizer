export default function ErrorMessage({ error, onDismiss }) {
  if (!error) return null;
  const title = error.status === 0
    ? 'Backend not reachable'
    : error.status === 402
    ? 'API credits exhausted'
    : error.status === 408
    ? 'Took too long'
    : 'Something went wrong';

  return (
    <div
      role="alert"
      className="w-full max-w-2xl mx-auto mt-8 p-5 rounded-lg bg-red-950/50 border border-red-800 text-red-100"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-xl">⚠️</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-red-200">{error.message}</p>
          {error.detail && (
            <p className="mt-2 text-xs text-red-300/80 font-mono break-all">{error.detail}</p>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-300 hover:text-red-100 text-sm"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
