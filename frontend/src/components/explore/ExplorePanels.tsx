import { useCallback, useState } from 'react';
import Pagination from '../chrome/Pagination';
import type { DetailedResult, ExploreResponse, RankedConfig } from '../../types';
import { displayDatabaseProvider } from '../../utils/storageLabels';
import { formatChunkDimensions } from './formatChunkDimensions';

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-green-500 transition-all duration-300"
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
    </div>
  );
}

function MethodBadge({ method, variant }: { method: string; variant: 'retrieval' | 'chunking' | 'model' }) {
  const colors = {
    retrieval: 'bg-orange-100 text-orange-700 border-orange-200',
    chunking: 'bg-slate-100 text-slate-700 border-slate-200',
    model: 'bg-blue-50 text-blue-700 border-blue-200',
  } as const;
  // variant is a typed union — safe lookup, not user-controlled injection.
  // eslint-disable-next-line security/detect-object-injection -- keyed by MethodBadge variant prop union
  const colorClass = colors[variant];
  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${colorClass}`}>
      {method.toUpperCase()}
    </span>
  );
}

export function BestParamsCard({ config }: { config: RankedConfig }) {
  const hasTies = config.tied_count && config.tied_count > 1;

  return (
    <div className="bg-slate-800 rounded-xl p-6 text-white">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-yellow-400 text-lg">&#127942;</span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Best Overall Parameters
          </span>
        </div>
        {hasTies && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-400/30">
            <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-xs text-amber-300 font-medium">
              {config.tied_count} configs tied at {config.max_score}%
            </span>
          </div>
        )}
      </div>

      {hasTies && (
        <div className="mb-4 p-3 rounded-lg bg-slate-700/50 border border-slate-600">
          <p className="text-xs text-slate-300 leading-relaxed">
            <span className="font-semibold text-amber-300">Tiebreaker applied:</span> When multiple configurations achieve the same max score,
            we rank by <strong>query avg score</strong> (weighted per-query average — each query contributes equally),
            then <strong>chunk size</strong> (smaller = faster), then <strong>overlap</strong> (smaller = less storage),
            then <strong>padding</strong> (smaller = less merge-forward padding).
          </p>
          <p className="text-xs text-slate-400 mt-2">
            ℹ️ Query avg is fairer than chunk avg because it prevents queries with many results from dominating the average.
            Configure via <code className="px-1 py-0.5 rounded bg-slate-800 text-amber-300">TIEBREAKER_METRIC</code> env var.
          </p>
        </div>
      )}

      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div className="flex gap-6">
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Database</div>
              <div className="text-sm font-bold uppercase text-indigo-300">{displayDatabaseProvider(config.database_provider)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Embed Provider</div>
              <div className="text-sm font-bold uppercase text-teal-300">{config.embedding_provider || 'local'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Embedding Model</div>
              <div className="text-lg font-bold">{config.embedding_model}</div>
            </div>
          </div>
          <div className="flex gap-8">
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Chunking</div>
              <div className="text-sm font-semibold capitalize">{config.chunking_method}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Chunk Size</div>
              <div className="text-sm font-semibold">{config.chunk_size}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Overlap</div>
              <div className="text-sm font-semibold">{config.overlap}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Padding</div>
              <div className="text-sm font-semibold">{config.padding ?? 0}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Retrieval</div>
              <div className="text-sm font-semibold capitalize">{config.retrieval_method}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Retrieval Provider</div>
              <div className="text-sm font-bold uppercase text-teal-300">{config.retrieval_provider || 'local'}</div>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Relevance Score</div>
          <div className="text-5xl font-black">
            {config.max_score}<span className="text-2xl text-slate-400">%</span>
          </div>
          <div className="text-xs text-slate-300 mt-2 space-y-0.5">
            <div className="flex items-center justify-end gap-1">
              <span className="text-slate-400">Query Avg:</span>
              <span className="font-semibold text-white">{config.query_avg_score}%</span>
              <span className="inline-flex items-center justify-center w-3 h-3 rounded-full bg-green-500/20 text-green-300 text-[10px]" title="Weighted per-query average (fairer)">✓</span>
            </div>
            <div className="flex items-center justify-end gap-1">
              <span className="text-slate-400">Chunk Avg:</span>
              <span className="text-slate-300">{config.avg_score}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigCard({ config, badge, annotation }: {
  config: RankedConfig;
  badge?: { icon: string; label: string; color: string };
  annotation?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold">
            #{config.rank}
          </span>
          {badge && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${badge.color}`}>
              <span>{badge.icon}</span>
              <span>{badge.label}</span>
            </span>
          )}
        </div>
        <div className="text-right">
          <span className="text-2xl font-black text-slate-800">{config.max_score}</span>
          <span className="text-sm text-slate-400 ml-0.5">MAX SCORE</span>
        </div>
      </div>

      {/* Annotation explaining why this config is ranked here */}
      {annotation && (
        <div className="mb-3 p-2 rounded bg-slate-50 border border-slate-200">
          <p className="text-xs text-slate-600 leading-relaxed">{annotation}</p>
        </div>
      )}

      <div className="space-y-2 text-sm">
        <div className="flex gap-2">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Database</span>
            <div className="font-bold text-indigo-700 text-xs uppercase">{displayDatabaseProvider(config.database_provider)}</div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Embed Prov</span>
            <div className="font-bold text-teal-700 text-xs uppercase">{config.embedding_provider || 'local'}</div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Embedding Model</span>
            <div className="font-mono text-slate-700 text-xs">{config.embedding_model}</div>
          </div>
        </div>
        <div className="flex gap-4">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Chunking</span>
            <div className="font-medium text-slate-700 capitalize">{config.chunking_method}</div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Size/Overlap/Pad</span>
            <div className="font-mono text-slate-700">{formatChunkDimensions(config)}</div>
          </div>
        </div>
        <div className="flex gap-3">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Retrieval</span>
            <div className="font-medium text-slate-700 capitalize">{config.retrieval_method}</div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Retrieval Prov</span>
            <div className="font-bold text-teal-700 text-xs uppercase">{config.retrieval_provider || 'local'}</div>
          </div>
        </div>
        <div className="space-y-1">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Query Avg</span>
            <div className="flex items-center gap-1">
              <span className="font-semibold text-slate-700">{config.query_avg_score}%</span>
              <span className="inline-flex items-center justify-center w-3 h-3 rounded-full bg-green-500/20 text-green-600 text-[9px]" title="Weighted per-query average (fairer)">✓</span>
            </div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Chunk Avg</span>
            <div className="font-medium text-slate-500">{config.avg_score}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function HyperparametersTab({ data }: { data: ExploreResponse }) {
  const topConfigs = data.ranked_configs.slice(0, 3);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(15);

  const handleItemsPerPageChange = useCallback((items: number) => {
    setItemsPerPage(items);
    setCurrentPage(1);
  }, []);

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedConfigs = data.ranked_configs.slice(startIndex, endIndex);

  // Detect ties: count how many of the top configs share the #1 max score
  const bestMaxScore = data.best_params?.max_score ?? 0;
  const tiedInTop3 = topConfigs.filter((c) => c.max_score === bestMaxScore).length;
  const hasTies = tiedInTop3 > 1;

  // Extract sweep dimensions from ranked_configs
  const uniqueModels = [...new Set(data.ranked_configs.map((c) => c.embedding_model))];
  const uniqueChunking = [...new Set(data.ranked_configs.map((c) => c.chunking_method))];
  const uniqueSizes = [...new Set(data.ranked_configs.map((c) => c.chunk_size))].sort((a, b) => a - b);
  const uniqueOverlaps = [...new Set(data.ranked_configs.map((c) => c.overlap))].sort((a, b) => a - b);
  const uniquePaddings = [...new Set(data.ranked_configs.map((c) => c.padding ?? 0))].sort((a, b) => a - b);
  const uniqueRetrievers = [...new Set(data.ranked_configs.map((c) => c.retrieval_method))];
  const totalConfigs = data.ranked_configs.length;

  const [sweepExpanded, setSweepExpanded] = useState(false);

  return (
    <div className="space-y-6">
      {/* Explanatory header */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
        <p className="text-sm text-purple-800">
          <strong>Aggregated configuration performance</strong> — Each card represents one unique parameter combination
          (chunking method + chunk size + overlap + padding + model + retrieval). Scores are averaged across all queries.
          See <strong>Detailed Results</strong> tab for individual chunk-level results.
        </p>
      </div>

      {/* Collapsible Sweep Dimensions */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setSweepExpanded(!sweepExpanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <svg
              className={`w-4 h-4 text-slate-400 transition-transform ${sweepExpanded ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <span className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Sweep Dimensions
            </span>
            <span className="text-xs text-slate-500">({totalConfigs} total configurations)</span>
          </div>
          <span className="text-xs text-slate-400">Click to {sweepExpanded ? 'collapse' : 'expand'}</span>
        </button>

        {sweepExpanded && (
          <div className="px-4 py-3 border-t border-slate-200 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Embedding Models ({uniqueModels.length})</div>
                <div className="flex flex-wrap gap-1.5">
                  {uniqueModels.map((m) => (
                    <span key={m} className="inline-flex px-2 py-1 text-xs font-mono rounded bg-blue-50 text-blue-700 border border-blue-200">
                      {m}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Retrieval Methods ({uniqueRetrievers.length})</div>
                <div className="flex flex-wrap gap-1.5">
                  {uniqueRetrievers.map((r) => (
                    <span key={r} className="inline-flex px-2 py-1 text-xs font-medium rounded bg-orange-50 text-orange-700 border border-orange-200 capitalize">
                      {r}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Chunking Methods ({uniqueChunking.length})</div>
                <div className="flex flex-wrap gap-1.5">
                  {uniqueChunking.map((ch) => (
                    <span key={ch} className="inline-flex px-2 py-1 text-xs font-medium rounded bg-slate-100 text-slate-700 border border-slate-200 capitalize">
                      {ch}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Chunk Sizes ({uniqueSizes.length})</div>
                  <div className="flex flex-wrap gap-1.5">
                    {uniqueSizes.map((s) => (
                      <span key={s} className="inline-flex px-2 py-1 text-xs font-mono rounded bg-purple-50 text-purple-700 border border-purple-200">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Overlaps ({uniqueOverlaps.length})</div>
                  <div className="flex flex-wrap gap-1.5">
                    {uniqueOverlaps.map((o) => (
                      <span key={o} className="inline-flex px-2 py-1 text-xs font-mono rounded bg-purple-50 text-purple-700 border border-purple-200">
                        {o}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1.5">Paddings ({uniquePaddings.length})</div>
                  <div className="flex flex-wrap gap-1.5">
                    {uniquePaddings.map((p) => (
                      <span key={p} className="inline-flex px-2 py-1 text-xs font-mono rounded bg-purple-50 text-purple-700 border border-purple-200">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs text-slate-500">
                <strong>Cartesian product:</strong> {uniqueModels.length} model{uniqueModels.length !== 1 ? 's' : ''} × {uniqueChunking.length} chunking method{uniqueChunking.length !== 1 ? 's' : ''} × {uniqueSizes.length} size{uniqueSizes.length !== 1 ? 's' : ''} × {uniqueOverlaps.length} overlap{uniqueOverlaps.length !== 1 ? 's' : ''} × {uniquePaddings.length} padding{uniquePaddings.length !== 1 ? 's' : ''} × {uniqueRetrievers.length} retriever{uniqueRetrievers.length !== 1 ? 's' : ''} = {totalConfigs} configuration{totalConfigs !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-lg font-bold text-slate-800 mb-1">Overall Corpus Performance</h3>
        <p className="text-sm text-slate-500">
          {hasTies ? (
            <>
              <strong>{tiedInTop3} configurations achieved {bestMaxScore}% max score.</strong>{' '}
              Ranked by query avg (weighted per-query average), then chunk size (smaller = faster), then overlap (smaller = less storage), then padding (smaller = less merge-forward).
            </>
          ) : (
            <>
              Top {Math.min(3, data.ranked_configs.length)} parameter configurations that yielded
              the highest relevance scores across the entire result set.
            </>
          )}
        </p>
      </div>

      {data.best_params && <BestParamsCard config={data.best_params} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {topConfigs.map((c, idx) => {
          // Determine badge and annotation based on whether this config is tied with #1
          let badge: { icon: string; label: string; color: string } | undefined;
          let annotation: string | undefined;

          if (hasTies && c.max_score === bestMaxScore) {
            if (idx === 0) {
              badge = { icon: '⭐', label: 'Best by tiebreaker', color: 'bg-yellow-50 text-yellow-700 border border-yellow-200' };
              // Explain WHY #1 wins tiebreaker (using query_avg_score)
              const reasons: string[] = [];
              if (c.query_avg_score > (topConfigs[1]?.query_avg_score ?? 0)) {
                reasons.push(`highest query avg (${c.query_avg_score}%)`);
              } else if (c.chunk_size < (topConfigs[1]?.chunk_size ?? Infinity)) {
                reasons.push(`smallest chunk size (${c.chunk_size} vs ${topConfigs[1]?.chunk_size})`);
              } else if (c.overlap < (topConfigs[1]?.overlap ?? Infinity)) {
                reasons.push(`smallest overlap (${c.overlap} vs ${topConfigs[1]?.overlap})`);
              } else if ((c.padding ?? 0) < (topConfigs[1]?.padding ?? Infinity)) {
                reasons.push(`smallest padding (${c.padding ?? 0} vs ${topConfigs[1]?.padding ?? 0})`);
              }
              annotation = reasons.length > 0
                ? `✓ Ranked #1 by: ${reasons.join(', ')} → faster processing + less storage`
                : `✓ Tied at ${c.max_score}% max score with identical parameters`;
            } else {
              badge = { icon: '🔀', label: 'Tied', color: 'bg-amber-50 text-amber-700 border border-amber-200' };
              // Explain why this config is ranked lower despite same max score (using query_avg_score)
              const diff: string[] = [];
              if (c.query_avg_score < (topConfigs[0]?.query_avg_score ?? 0)) {
                diff.push(`lower query avg (${c.query_avg_score}% vs ${topConfigs[0].query_avg_score}%)`);
              } else if (c.chunk_size > (topConfigs[0]?.chunk_size ?? 0)) {
                diff.push(`larger chunks (${c.chunk_size} vs ${topConfigs[0].chunk_size})`);
              } else if (c.overlap > (topConfigs[0]?.overlap ?? 0)) {
                diff.push(`larger overlap (${c.overlap} vs ${topConfigs[0].overlap})`);
              } else if ((c.padding ?? 0) > (topConfigs[0]?.padding ?? 0)) {
                diff.push(`larger padding (${c.padding ?? 0} vs ${topConfigs[0].padding ?? 0})`);
              }
              annotation = diff.length > 0
                ? `⚡ Same max score (${c.max_score}%), but: ${diff.join(', ')}`
                : `⚡ Tied at ${c.max_score}% — identical performance`;
            }
          }

          return (
            <ConfigCard
              key={`${c.database_provider}-${c.embedding_provider}-${c.embedding_model}-${c.chunking_method}-${c.chunk_size}-${c.overlap}-${c.padding ?? 0}-${c.retrieval_method}-${c.retrieval_provider}`}
              config={c}
              badge={badge}
              annotation={annotation}
            />
          );
        })}
      </div>

      {data.ranked_configs.length > 3 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
            <h4 className="text-sm font-bold text-slate-600 uppercase tracking-wider">
              All Configurations ({data.ranked_configs.length})
            </h4>
          </div>
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Rank</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">DB</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Embed Prov</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Embedding Model</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Chunking</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Size/Overlap/Pad</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Retrieval</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Retrieval Prov</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Max Score</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Avg Score</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Results</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedConfigs.map((c) => (
                <tr key={`row-${c.rank}`} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-sm font-bold text-slate-600">#{c.rank}</td>
                  <td className="px-4 py-2.5 text-xs font-bold text-indigo-700 uppercase">{displayDatabaseProvider(c.database_provider)}</td>
                  <td className="px-4 py-2.5 text-xs font-bold text-teal-700 uppercase">{c.embedding_provider || 'local'}</td>
                  <td className="px-4 py-2.5 text-sm font-mono text-slate-700">{c.embedding_model}</td>
                  <td className="px-4 py-2.5 text-sm capitalize">{c.chunking_method}</td>
                  <td className="px-4 py-2.5 text-sm font-mono">{formatChunkDimensions(c)}</td>
                  <td className="px-4 py-2.5"><MethodBadge method={c.retrieval_method} variant="retrieval" /></td>
                  <td className="px-4 py-2.5 text-xs font-bold text-teal-700 uppercase">{c.retrieval_provider || 'local'}</td>
                  <td className="px-4 py-2.5 text-sm font-bold">{c.max_score}%</td>
                  <td className="px-4 py-2.5 text-sm">{c.avg_score}%</td>
                  <td className="px-4 py-2.5 text-sm text-slate-500">{c.result_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            currentPage={currentPage}
            totalItems={data.ranked_configs.length}
            itemsPerPage={itemsPerPage}
            onPageChange={setCurrentPage}
            onItemsPerPageChange={handleItemsPerPageChange}
            selectId="explorer-hyperparams-per-page"
          />
        </div>
      )}
    </div>
  );
}

export function DetailedResultsTab({ results }: { results: DetailedResult[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(15);

  const handleItemsPerPageChange = useCallback((items: number) => {
    setItemsPerPage(items);
    setCurrentPage(1);
  }, []);

  const toggleExpand = useCallback((rank: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(rank)) {
        next.delete(rank);
      } else {
        next.add(rank);
      }
      return next;
    });
  }, []);

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedResults = results.slice(startIndex, endIndex);

  return (
    <div className="space-y-4">
      {/* Explanatory header */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-sm text-blue-800">
          <strong>Individual chunk results</strong> — Each row shows one retrieved chunk from one query.
          Multiple rows may share the same config (chunking + size/overlap/padding).
          See <strong>Hyperparameters</strong> tab for aggregated config performance.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="divide-y divide-slate-100">
          {paginatedResults.map((r) => {
            const isExpanded = expanded.has(r.rank);
            const truncatedText = r.chunk_text.length > 120
              ? r.chunk_text.slice(0, 120) + '...'
              : r.chunk_text;
            const truncatedQuery = r.query_text && r.query_text.length > 60
              ? r.query_text.slice(0, 60) + '...'
              : r.query_text;

            return (
              <div
                key={r.rank}
                className="px-4 py-3 hover:bg-slate-50 transition-colors"
              >
                {/* Top row: rank, score, config params */}
                <div className="flex items-start gap-4 mb-2">
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="inline-flex items-center justify-center w-8 h-6 rounded bg-blue-600 text-white text-xs font-bold">
                      #{r.rank}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 w-[140px]">
                    <ScoreBar score={r.score} />
                    <span className="text-sm font-bold text-slate-800 w-8 text-right">{r.score}</span>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    <div className="shrink-0">
                      <span className="text-xs font-mono text-slate-500">{r.embedding_model}</span>
                    </div>

                    <div className="shrink-0">
                      <MethodBadge method={r.retrieval_method} variant="retrieval" />
                    </div>

                    <div className="shrink-0">
                      <MethodBadge method={r.chunking_method} variant="chunking" />
                    </div>

                    {/* Show chunk_size/overlap/padding to map back to configs */}
                    <div className="shrink-0">
                      <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-purple-50 text-purple-700 border border-purple-200">
                        {formatChunkDimensions(r)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Query text (if available) */}
                {r.query_text && (
                  <div className="mb-2 pl-11">
                    <span className="text-xs text-slate-400 uppercase tracking-wider mr-2">Query:</span>
                    <span className="text-xs text-slate-600 italic">"{truncatedQuery}"</span>
                  </div>
                )}

                {/* Chunk text */}
                <div
                  className="pl-11 cursor-pointer"
                  onClick={() => toggleExpand(r.rank)}
                >
                  <p className="text-sm text-slate-600 leading-snug">
                    &ldquo;{isExpanded ? r.chunk_text : truncatedText}&rdquo;
                  </p>
                  {!isExpanded && r.chunk_text.length > 120 && (
                    <button className="text-xs text-blue-600 hover:text-blue-800 mt-1">
                      Click to expand
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <Pagination
          currentPage={currentPage}
          totalItems={results.length}
          itemsPerPage={itemsPerPage}
          onPageChange={setCurrentPage}
          onItemsPerPageChange={handleItemsPerPageChange}
          selectId="explorer-detailed-per-page"
        />
      </div>
    </div>
  );
}

export function ConfigSidebar({ data, selectedMethods, onToggleMethod }: {
  data: ExploreResponse;
  selectedMethods: Set<string>;
  onToggleMethod: (method: string) => void;
}) {
  const allMethods = [...new Set(data.ranked_configs.map((c) => c.retrieval_method))];
  const [configsExpanded, setConfigsExpanded] = useState(false);

  const displayedConfigs = configsExpanded
    ? data.ranked_configs
    : data.ranked_configs.slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <button
          onClick={() => setConfigsExpanded(!configsExpanded)}
          className="w-full flex items-center justify-between mb-3 text-left hover:text-slate-200 transition-colors"
        >
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Target Configurations
          </h3>
          <span className="text-slate-400 text-xs">
            {configsExpanded ? '▲' : '▼'} {data.ranked_configs.length}
          </span>
        </button>
        <div className="space-y-1.5">
          {displayedConfigs.map((c) => (
            <div
              key={`sidebar-${c.rank}`}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700/50 text-white text-sm"
            >
              <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-xs truncate">
                  {c.chunking_method}/{formatChunkDimensions(c)}
                </div>
                <div className="text-xs text-slate-400">{c.result_count} results</div>
              </div>
            </div>
          ))}
          {!configsExpanded && data.ranked_configs.length > 5 && (
            <button
              onClick={() => setConfigsExpanded(true)}
              className="w-full px-3 py-2 rounded-lg bg-slate-700/30 text-slate-300 text-xs hover:bg-slate-700/50 transition-colors"
            >
              + {data.ranked_configs.length - 5} more
            </button>
          )}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
          Search Parameters
        </h3>
        <div className="mb-2 text-xs text-slate-300 font-medium">Retrieval Methods</div>
        <div className="space-y-1.5">
          {allMethods.map((method) => (
            <label
              key={method}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700/50 text-white text-sm cursor-pointer hover:bg-slate-700"
            >
              <input
                type="checkbox"
                checked={selectedMethods.has(method)}
                onChange={() => onToggleMethod(method)}
                className="rounded border-slate-500 text-blue-500 focus:ring-blue-500"
              />
              <span className="capitalize">{method}</span>
              <span className="text-xs text-slate-400 ml-auto">
                ({method === 'dense' ? 'Vector Similarity' : method === 'sparse' ? 'Keyword BM25' : 'Dense + Sparse'})
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="text-xs text-slate-400 pt-2 border-t border-slate-700">
        <div>Configs: {data.ranked_configs.length}</div>
        <div>Total matches: {data.total_matches}</div>
      </div>
    </div>
  );
}
