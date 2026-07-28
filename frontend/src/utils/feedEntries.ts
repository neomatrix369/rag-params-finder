import type { FeedEntry } from '../components/chrome/LoadingFeedbackPanel';

let feedSeq = 0;

/** Append one activity-feed line with a unique id (shared across screens). */
export function appendFeedEntry(
  prev: FeedEntry[],
  text: string,
  variant: FeedEntry['variant'],
): FeedEntry[] {
  feedSeq += 1;
  return [...prev, { id: `${Date.now()}-${feedSeq}`, text, variant }];
}
