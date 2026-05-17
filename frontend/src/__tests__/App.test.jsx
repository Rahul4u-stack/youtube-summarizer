import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

// Mock the api module so we never hit the network from a test
vi.mock('../api', () => ({
  apiBase: 'http://localhost:5001',
  ApiError: class ApiError extends Error {
    constructor(msg, opts = {}) {
      super(msg);
      this.name = 'ApiError';
      this.status = opts.status;
      this.detail = opts.detail;
    }
  },
  summarize: vi.fn(),
  // Default to "unreachable" so the demo banner stays hidden in tests.
  // Individual tests can override per-call if they want to assert banner state.
  health: vi.fn().mockResolvedValue({ ok: false }),
}));

import { summarize } from '../api';

const STUB_PAYLOAD = {
  video: {
    title: 'Stub Video',
    channel: 'Stub Channel',
    duration_seconds: 600,
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    thumbnail_url: null,
  },
  transcript: { full_text: 'transcript text', word_count: 2, language: 'en' },
  summary: {
    executive_summary: 'A summary.',
    key_insights: ['one', 'two', 'three'],
    action_items: [],
    topics_covered: ['a', 'b', 'c'],
    tone: 'casual',
  },
  metadata: {
    generated_at: '2026-05-16T00:00:00+00:00',
    model: 'claude-sonnet-4-6',
    tokens_used: 1234,
    cache_hit: false,
    pipeline_seconds: 17.0,
  },
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('App', () => {
  it('renders the heading and form', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /youtube/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/youtube url/i)).toBeInTheDocument();
  });

  it('disables the submit button until a valid URL is entered', () => {
    render(<App />);
    const button = screen.getByRole('button', { name: /summarize/i });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/youtube url/i), {
      target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
    });
    expect(button).not.toBeDisabled();
  });

  it('shows the summary card on success and updates history', async () => {
    summarize.mockResolvedValueOnce(STUB_PAYLOAD);
    render(<App />);

    fireEvent.change(screen.getByLabelText(/youtube url/i), {
      target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /summarize/i }));

    await waitFor(() => {
      // Use a heading-specific selector because the title also appears in
      // the history sidebar items (JSDOM doesn't respect responsive `hidden`
      // classes, so both desktop & mobile sidebar copies are in the DOM).
      expect(screen.getByRole('heading', { name: 'Stub Video' })).toBeInTheDocument();
    });
    expect(screen.getByText(/executive summary/i)).toBeInTheDocument();
    expect(screen.getByText('one')).toBeInTheDocument();

    // History persisted to localStorage
    const stored = JSON.parse(localStorage.getItem('yts:history:v1') || '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].title).toBe('Stub Video');
  });

  it('shows an error message when the API fails', async () => {
    const { ApiError } = await import('../api');
    summarize.mockRejectedValueOnce(new ApiError('Backend unreachable', { status: 0 }));
    render(<App />);

    fireEvent.change(screen.getByLabelText(/youtube url/i), {
      target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /summarize/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    expect(screen.getByText(/backend unreachable/i)).toBeInTheDocument();
  });
});
