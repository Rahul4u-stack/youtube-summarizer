export default function LoadingState({ coldStart }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="w-full max-w-2xl mx-auto mt-8 p-6 rounded-lg bg-secondary border border-slate-700"
    >
      <div className="flex items-center gap-3">
        <span
          className="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin"
          aria-hidden="true"
        />
        <span className="text-slate-200 font-medium">Working on it…</span>
      </div>
      <ul className="mt-4 space-y-1 text-sm text-slate-400">
        <li>1. Downloading the audio (~5–10s)</li>
        <li>2. Transcribing with Whisper.cpp (~30–90s depending on length)</li>
        <li>3. Summarizing with Claude (~3–5s)</li>
      </ul>
      {coldStart && (
        <p className="mt-4 text-sm text-amber-300">
          The backend looks cold — Render free tier sleeps after 15&nbsp;min of inactivity and takes ~30&nbsp;s to wake up. Hang tight.
        </p>
      )}
    </div>
  );
}
