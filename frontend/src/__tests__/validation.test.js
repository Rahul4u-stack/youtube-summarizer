import { describe, it, expect } from 'vitest';
import { isValidYoutubeUrl, formatDuration } from '../validation';

describe('isValidYoutubeUrl', () => {
  it.each([
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com/watch?v=dQw4w9WgXcQ',
    'http://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtu.be/dQw4w9WgXcQ',
    'https://youtube.com/shorts/dQw4w9WgXcQ',
  ])('accepts %s', (url) => {
    expect(isValidYoutubeUrl(url)).toBe(true);
  });

  it.each([
    '',
    'not a url',
    'https://vimeo.com/12345',
    'https://www.youtube.com/',
    'https://youtube.com/watch?v=tooshort',
    'https://example.com/watch?v=dQw4w9WgXcQ',
  ])('rejects %s', (url) => {
    expect(isValidYoutubeUrl(url)).toBe(false);
  });

  it('rejects non-string inputs', () => {
    expect(isValidYoutubeUrl(null)).toBe(false);
    expect(isValidYoutubeUrl(undefined)).toBe(false);
    expect(isValidYoutubeUrl(123)).toBe(false);
  });
});

describe('formatDuration', () => {
  it('formats sub-hour durations as M:SS', () => {
    expect(formatDuration(19)).toBe('0:19');
    expect(formatDuration(125)).toBe('2:05');
    expect(formatDuration(3599)).toBe('59:59');
  });

  it('formats hour-plus durations as H:MM:SS', () => {
    expect(formatDuration(3600)).toBe('1:00:00');
    expect(formatDuration(3661)).toBe('1:01:01');
  });

  it('handles 0 and undefined', () => {
    expect(formatDuration(0)).toBe('0:00');
    expect(formatDuration(undefined)).toBe('0:00');
  });
});
