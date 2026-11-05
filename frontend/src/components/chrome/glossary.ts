/**
 * Slice 67 glossary: the one place the dashboard's number words are defined.
 * Pure fixed strings in a stable order; no counts are computed here.
 * The retired word for a distinct parameter set must not appear in any entry.
 */
export type GlossaryEntry = { term: string; definition: string };

export const GLOSSARY: readonly GlossaryEntry[] = [
  { term: 'Run', definition: 'One executed pipeline pass: parse, chunk, embed, store, query. Counts of runs are runs that have actually started.' },
  { term: 'Planned runs', definition: 'The number of runs the sweep is expected to execute, worked out from the config before anything starts. Shown as "est." when it is an estimate.' },
  { term: 'Configuration', definition: 'One distinct set of parameters (model, chunking, size, overlap, retriever). The sweep header counts configurations.' },
  { term: 'Trial', definition: 'One Bayesian-search attempt. Only Bayesian sweeps have trials; grid sweeps have runs.' },
  { term: 'Query result', definition: 'The top-K chunks a run returned for one query.' },
  { term: 'Golden query / record', definition: 'A query with a known good answer in the dataset, used to judge whether a run found the right chunk.' },
  { term: 'Similarity score', definition: 'The highest single-chunk similarity found in a run (the max, not the average), normalised per group to 0 to 100.' },
  { term: 'Lone run = 100', definition: 'A group with one run has nothing to compare against, so min-max normalisation makes it 100 by construction.' },
  { term: 'Observed vs planned', definition: 'Observed is what the stored data shows now; planned is what the config says should happen. They differ while a sweep is running or after a cancel.' },
  { term: 'Est. (estimated)', definition: 'A figure derived from a fixed formula rather than measured, for example storage size.' },
];
