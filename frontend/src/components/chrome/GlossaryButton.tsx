import { useCallback, useRef, useState } from 'react';
import Dialog from './Dialog';
import { GLOSSARY } from './glossary';

/** Header button that opens the Glossary dialog and gets focus back when it closes. */
export default function GlossaryButton({ isDark = false }: { isDark?: boolean }) {
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
        Glossary
      </button>
      <Dialog open={open} onClose={close} title="Glossary" returnFocusRef={buttonRef}>
        <dl className="space-y-4">
          {GLOSSARY.map(({ term, definition }) => (
            <div key={term}>
              <dt className="text-sm font-semibold text-ink">{term}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-muted">{definition}</dd>
            </div>
          ))}
        </dl>
      </Dialog>
    </>
  );
}
