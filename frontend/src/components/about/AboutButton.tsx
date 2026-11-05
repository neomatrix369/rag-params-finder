import { useCallback, useRef, useState } from 'react';
import AboutDialog from './AboutDialog';

/** Header button that opens the About dialog and gets focus back when it closes. */
export default function AboutButton({ isDark = false }: { isDark?: boolean }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
        className={`mt-3 min-h-11 rounded-lg border px-3 text-xs font-semibold ${
          isDark
            ? 'border-white/30 text-white hover:bg-white/10'
            : 'border-line text-ink hover:bg-canvas'
        }`}
      >
        About
      </button>
      <AboutDialog open={open} onClose={close} returnFocusRef={buttonRef} />
    </>
  );
}
