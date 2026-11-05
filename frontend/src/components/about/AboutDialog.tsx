import type { RefObject } from 'react';
import { ABOUT_SECTIONS, resolveAboutAsset, type AboutSection } from '../../demo/about';
import Dialog from '../chrome/Dialog';
import MarkdownView from './MarkdownView';

type AboutDialogProps = {
  open: boolean;
  onClose: () => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  /** Defaults to the bundled docs/about sections; tests and callers may pass a subset. */
  sections?: AboutSection[];
};

/** About box (Slice 56 Part C1): the bundled docs/about sections in file-name order, offline. */
export default function AboutDialog({
  open,
  onClose,
  returnFocusRef,
  sections = ABOUT_SECTIONS,
}: AboutDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} title="About RAG Params Finder" returnFocusRef={returnFocusRef}>
      {sections.map((section) => (
        <section key={section.id} data-section={section.id} className="mb-6 last:mb-0">
          <MarkdownView source={section.markdown} headingOffset={2} resolveImage={resolveAboutAsset} />
        </section>
      ))}
    </Dialog>
  );
}
