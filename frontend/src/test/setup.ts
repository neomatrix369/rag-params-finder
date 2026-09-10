import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  // Fake timers left active after a poll/timer test hang waitFor in later suites
  // (shared worker pool). Always restore before cleanup.
  vi.useRealTimers();
  cleanup();
  localStorage.clear();
});
