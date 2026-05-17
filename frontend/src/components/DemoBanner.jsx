export default function DemoBanner({ show }) {
  if (!show) return null;
  return (
    <div
      role="status"
      className="max-w-3xl mx-auto mb-8 p-4 rounded-lg bg-amber-950/60 border border-amber-700/60 text-amber-100"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-xl">🧪</span>
        <div className="flex-1 text-sm">
          <p className="font-semibold text-amber-200">Demo mode</p>
          <p className="mt-1 text-amber-100/90">
            This live site returns sample responses, not real transcriptions —
            the production server doesn't host Whisper.cpp + the 140&nbsp;MB model
            file on free-tier hardware. The full pipeline (yt-dlp → Whisper.cpp →
            Claude with prompt caching) runs locally — see{' '}
            <a
              href="https://github.com/Rahul4u-stack/youtube-summarizer#local-dev-backend"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-amber-50"
            >
              the README
            </a>{' '}
            for setup.
          </p>
        </div>
      </div>
    </div>
  );
}
