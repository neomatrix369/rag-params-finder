import type { RefObject } from 'react';
import { ABOUT_SECTIONS, type AboutSection } from '../../walkthru/about';
import { useWalkthruActions } from '../../walkthru/WalkthruContext';
import Dialog from '../chrome/Dialog';
import MarkdownView from './MarkdownView';

type AboutDialogProps = {
  open: boolean;
  onClose: () => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  /** Defaults to the bundled docs/about sections; tests and callers may pass a subset. */
  sections?: AboutSection[];
};

/**
 * About box (Slice 56 Part C1): the bundled docs/about sections in file-name order, offline.
 * When the App's Walkthru context is available (Part C2), it also offers the two demo entry
 * points - Start Walkthru and Open the demo; both close the dialog first.
 */
export default function AboutDialog({
  open,
  onClose,
  returnFocusRef,
  sections = ABOUT_SECTIONS,
}: AboutDialogProps) {
  const { startWalkthru, openDemo, available } = useWalkthruActions();

  return (
    <Dialog open={open} onClose={onClose} title="About RAG Params Finder" returnFocusRef={returnFocusRef}>
      {available ? (
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              onClose();
              startWalkthru();
            }}
            className="min-h-11 rounded-lg border border-accent bg-accent-soft px-4 text-sm font-semibold text-accent-strong"
          >
            ▶ Start Walkthru
          </button>
          <button
            type="button"
            onClick={() => {
              onClose();
              openDemo();
            }}
            className="min-h-11 rounded-lg border border-line bg-paper px-4 text-sm font-semibold text-ink hover:border-accent"
          >
            Open the demo
          </button>
        </div>
      ) : null}
      {sections.map((section) => (
        <section key={section.id} data-section={section.id} className="mb-6 last:mb-0">
          <MarkdownView source={section.markdown} headingOffset={2} />
        </section>
      ))}
    </Dialog>
  );
}
