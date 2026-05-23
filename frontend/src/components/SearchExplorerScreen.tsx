import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DETAIL_POLL_MS,
  DEV_POLL_LOG_INTERVAL_MS,
  LOADING_STALL_AFTER_MS,
  LOADING_STALL_REPEAT_MS,
} from '../constants';
import AppPageChrome from './AppPageChrome';
import DashboardShell from './DashboardShell';
import LoadingFeedbackPanel from './LoadingFeedbackPanel';
import PollingIndicator from './PollingIndicator';
import type { FeedEntry } from './LoadingFeedbackPanel';
import {
  getExperiment,
  getExperimentExplore,
  getExperimentExploreWithProgress,
  type ExperimentProgressCallback,
} from '../services/apiClient';
import { createStallWatcher, formatBytes, type FetchProgressUpdate } from '../services/fetchWithProgress';
import { DetailedResult, ExploreResponse, RankedConfig } from '../types';
import { devInfo, devInfoThrottled, devWarn } from '../utils/devLog';

let xfSeq = 0;

function xfAppend(prev: FeedEntry[], text: string, variant: FeedEntry['variant']): FeedEntry[] {
  xfSeq += 1;
  return [...prev, { id: `${Date.now()}-${xfSeq}`, text, variant }];
}

type Tab = 'hyperparameters' | 'detailed';

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
  };
  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${colors[variant]}`}>
      {method.toUpperCase()}
    </span>
  );
}

function BestParamsCard({ config }: { config: RankedConfig }) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 text-white">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-yellow-400 text-lg">&#127942;</span>
        <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
          Best Overall Parameters
        </span>
      </div>

      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div className="flex gap-6">
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Database</div>
              <div className="text-sm font-bold uppercase text-indigo-300">{config.database_provider || 'mongodb'}</div>
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
              <div className="text-xs text-slate-400 uppercase tracking-wider">Retrieval</div>
              <div className="text-sm font-semibold capitalize">{config.retrieval_method}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400 uppercase tracking-wider">Rerank Provider</div>
              <div className="text-sm font-bold uppercase text-teal-300">{config.rerank_provider || 'local'}</div>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Relevance Score</div>
          <div className="text-5xl font-black">
            {config.max_score}<span className="text-2xl text-slate-400">%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigCard({ config }: { config: RankedConfig }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold">
          #{config.rank}
        </span>
        <div className="text-right">
          <span className="text-2xl font-black text-slate-800">{config.max_score}</span>
          <span className="text-sm text-slate-400 ml-0.5">MAX SCORE</span>
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex gap-2">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Database</span>
            <div className="font-bold text-indigo-700 text-xs uppercase">{config.database_provider || 'mongodb'}</div>
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
            <span className="text-xs text-slate-400 uppercase tracking-wider">Size/Overlap</span>
            <div className="font-mono text-slate-700">{config.chunk_size}/{config.overlap}</div>
          </div>
        </div>
        <div className="flex gap-3">
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Retrieval</span>
            <div className="font-medium text-slate-700 capitalize">{config.retrieval_method}</div>
          </div>
          <div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Rerank Prov</span>
            <div className="font-bold text-teal-700 text-xs uppercase">{config.rerank_provider || 'local'}</div>
          </div>
        </div>
        <div>
          <span className="text-xs text-slate-400 uppercase tracking-wider">Avg Score</span>
          <div className="font-medium text-slate-700">{config.avg_score}%</div>
        </div>
      </div>
    </div>
  );
}

function Pagination({
  currentPage,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
}: {
  currentPage: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (items: number) => void;
}) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200">
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-600">
          Showing <span className="font-medium">{startItem}</span> to{' '}
          <span className="font-medium">{endItem}</span> of{' '}
          <span className="font-medium">{totalItems}</span>
        </span>
        <div className="flex items-center gap-2">
          <label htmlFor="items-per-page" className="text-sm text-slate-600">
            Per page:
          </label>
          <select
            id="items-per-page"
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            <option value={10}>10</option>
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
        >
          Previous
        </button>
        <span className="text-sm text-slate-600">
          Page <span className="font-medium">{currentPage}</span> of{' '}
          <span className="font-medium">{totalPages}</span>
        </span>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function HyperparametersTab({ data }: { data: ExploreResponse }) {
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

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-slate-800 mb-1">Overall Corpus Performance</h3>
        <p className="text-sm text-slate-500">
          Top {Math.min(3, data.ranked_configs.length)} parameter configurations that yielded
          the highest relevance scores across the entire result set.
        </p>
      </div>

      {data.best_params && <BestParamsCard config={data.best_params} />}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {topConfigs.map((c) => (
          <ConfigCard key={`${c.database_provider}-${c.embedding_provider}-${c.embedding_model}-${c.chunking_method}-${c.chunk_size}-${c.overlap}-${c.retrieval_method}-${c.rerank_provider}`} config={c} />
        ))}
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
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Size/Overlap</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Retrieval</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Rerank Prov</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Max Score</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Avg Score</th>
                <th className="px-4 py-2 text-left text-xs font-bold text-slate-500 uppercase">Results</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedConfigs.map((c) => (
                <tr key={`row-${c.rank}`} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-sm font-bold text-slate-600">#{c.rank}</td>
                  <td className="px-4 py-2.5 text-xs font-bold text-indigo-700 uppercase">{c.database_provider || 'mongodb'}</td>
                  <td className="px-4 py-2.5 text-xs font-bold text-teal-700 uppercase">{c.embedding_provider || 'local'}</td>
                  <td className="px-4 py-2.5 text-sm font-mono text-slate-700">{c.embedding_model}</td>
                  <td className="px-4 py-2.5 text-sm capitalize">{c.chunking_method}</td>
                  <td className="px-4 py-2.5 text-sm font-mono">{c.chunk_size}/{c.overlap}</td>
                  <td className="px-4 py-2.5"><MethodBadge method={c.retrieval_method} variant="retrieval" /></td>
                  <td className="px-4 py-2.5 text-xs font-bold text-teal-700 uppercase">{c.rerank_provider || 'local'}</td>
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
          />
        </div>
      )}
    </div>
  );
}

function DetailedResultsTab({ results }: { results: DetailedResult[] }) {
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
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="divide-y divide-slate-100">
        {paginatedResults.map((r) => {
          const isExpanded = expanded.has(r.rank);
          const truncatedText = r.chunk_text.length > 120
            ? r.chunk_text.slice(0, 120) + '...'
            : r.chunk_text;

          return (
            <div
              key={r.rank}
              className="flex items-start gap-4 px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer"
              onClick={() => toggleExpand(r.rank)}
            >
              <div className="flex items-center gap-3 shrink-0 pt-0.5">
                <span className="inline-flex items-center justify-center w-8 h-6 rounded bg-blue-600 text-white text-xs font-bold">
                  #{r.rank}
                </span>
              </div>

              <div className="flex items-center gap-2 shrink-0 w-[140px] pt-0.5">
                <ScoreBar score={r.score} />
                <span className="text-sm font-bold text-slate-800 w-8 text-right">{r.score}</span>
              </div>

              <div className="shrink-0 pt-0.5">
                <span className="text-xs font-mono text-slate-500">{r.embedding_model}</span>
              </div>

              <div className="shrink-0 pt-0.5">
                <MethodBadge method={r.retrieval_method} variant="retrieval" />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-600 leading-snug">
                  &ldquo;{isExpanded ? r.chunk_text : truncatedText}&rdquo;
                </p>
              </div>

              <div className="shrink-0 pt-0.5 text-right">
                <span className="text-xs text-slate-400 uppercase tracking-wider">
                  {r.chunking_method}
                </span>
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
      />
    </div>
  );
}

function ConfigSidebar({ data, selectedMethods, onToggleMethod }: {
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
                  {c.chunking_method}/{c.chunk_size}+{c.overlap}
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

export default function SearchExplorerScreen({
  experimentId,
  onBack,
}: {
  experimentId: string;
  onBack: () => void;
}) {
  const [data, setData] = useState<ExploreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** True on first paint so we never flash an empty canvas before the fetch effect runs */
  const [loading, setLoading] = useState(true);
  const [isPolling, setIsPolling] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('hyperparameters');
  const [selectedQuery, setSelectedQuery] = useState<string>('');
  const [selectedMethods, setSelectedMethods] = useState<Set<string>>(new Set());
  const [pollWhileRunning, setPollWhileRunning] = useState(true);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [receivedBytes, setReceivedBytes] = useState<number | null>(null);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);

  const selectedQueryRef = useRef(selectedQuery);
  selectedQueryRef.current = selectedQuery;

  const prevExperimentRef = useRef('');
  const aliveRef = useRef(true);
  const pollDevLogAtRef = useRef(new Map<string, number>());

  useEffect(() => {
    setPollWhileRunning(true);
    setSelectedQuery('');
  }, [experimentId]);

  useEffect(() => {
    aliveRef.current = true;
    const abort = new AbortController();
    let switchedExperiment = prevExperimentRef.current !== experimentId;
    if (switchedExperiment) {
      prevExperimentRef.current = experimentId;
      setData(null);
    }

    const stall = createStallWatcher({
      scope: 'SearchExplorerScreen',
      operation: 'explore hydrate',
      alive: () => aliveRef.current,
      afterMs: LOADING_STALL_AFTER_MS,
      repeatMs: LOADING_STALL_REPEAT_MS,
      onWarning: (text) => setFeed((f) => xfAppend(f, text, 'warning')),
    });

    const applyProg: ExperimentProgressCallback = (u: FetchProgressUpdate) => {
      if (!aliveRef.current) return;
      if (u.type === 'downloading') {
        setReceivedBytes(u.receivedBytes);
        setTotalBytes(u.totalBytes);
        return;
      }
      setFeed((f) => xfAppend(f, u.text, u.variant === 'warning' ? 'warning' : 'default'));
    };

    async function fetchExplore() {
      devInfo(
        'SearchExplorerScreen',
        `hydrate started — ${experimentId.slice(0, 8)}…${selectedQuery ? ' (filtered query)' : ''}`,
      );
      setLoading(true);
      setReceivedBytes(null);
      setTotalBytes(null);
      if (switchedExperiment) {
        setFeed([{ id: 'x0', text: 'Fetching explorer aggregates (Mongo + analyzer)…', variant: 'default' }]);
      } else {
        setFeed((f) =>
          xfAppend(
            f,
            `Refreshing explorer${selectedQuery ? ' (filtered query)' : ''}…`,
            'default',
          ),
        );
      }
      setError(null);
      stall.start();
      try {
        const payload = await getExperimentExploreWithProgress(
          experimentId,
          selectedQuery || undefined,
          applyProg,
          abort.signal,
        );
        stall.stop();
        if (!aliveRef.current) return;
        setFeed((f) => xfAppend(f, 'Explorer snapshot ready.', 'default'));
        setData(payload);
        devInfo(
          'SearchExplorerScreen',
          `hydrate OK — ${payload.ranked_configs.length} configs, ${payload.query_count} quer${payload.query_count === 1 ? 'y' : 'ies'}`,
        );

        setSelectedMethods((prev) => {
          if (prev.size > 0) return prev;
          return new Set(payload.ranked_configs.map((c) => c.retrieval_method));
        });
      } catch (err) {
        stall.stop();
        if (!aliveRef.current) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg =
          err instanceof Error ? err.message : 'Failed to fetch experiment explore data';
        devWarn('SearchExplorerScreen', `hydrate failed — ${experimentId.slice(0, 8)}… — ${msg}`);
        setError(msg);
        setFeed((f) => xfAppend(f, `Failed: ${msg}`, 'warning'));
      } finally {
        stall.stop();
        if (aliveRef.current) setLoading(false);
      }
    }

    void fetchExplore();

    return () => {
      aliveRef.current = false;
      abort.abort();
      stall.stop();
    };
  }, [experimentId, selectedQuery]);

  useEffect(() => {
    if (!pollWhileRunning) {
      return;
    }
    const id = window.setInterval(() => {
      void (async () => {
        setIsPolling(true);
        try {
          const exp = await getExperiment(experimentId);
          if (exp.status !== 'running') {
            setPollWhileRunning(false);
            return;
          }
          const response = await getExperimentExplore(
            experimentId,
            selectedQueryRef.current || undefined,
          );
          setData(response);
          setError(null);
          devInfoThrottled(
            'SearchExplorerScreen',
            `poll:explore:${experimentId}`,
            DEV_POLL_LOG_INTERVAL_MS,
            `explore poll OK — ${response.ranked_configs.length} configs`,
            pollDevLogAtRef.current,
          );
          setSelectedMethods((prev) => {
            if (prev.size > 0) {
              return prev;
            }
            return new Set(response.ranked_configs.map((c) => c.retrieval_method));
          });
        } catch (pollErr) {
          devWarn('SearchExplorerScreen', `explore poll failed — ${experimentId.slice(0, 8)}… — ${String(pollErr)}`);
        } finally {
          setIsPolling(false);
        }
      })();
    }, DETAIL_POLL_MS);
    return () => window.clearInterval(id);
  }, [experimentId, pollWhileRunning]);

  const handleToggleMethod = useCallback((method: string) => {
    setSelectedMethods((prev) => {
      const next = new Set(prev);
      if (next.has(method)) {
        /** Never leave zero methods checked — avoids a blank explorer body */
        if (next.size <= 1) return prev;
        next.delete(method);
        return next;
      }
      next.add(method);
      return next;
    });
  }, []);

  const filteredResults = data
    ? data.detailed_results.filter((r) => selectedMethods.has(r.retrieval_method))
    : [];

  const filteredConfigs = data
    ? data.ranked_configs.filter((c) => selectedMethods.has(c.retrieval_method))
    : [];

  const filteredData = data
    ? { ...data, detailed_results: filteredResults, ranked_configs: filteredConfigs }
    : null;

  const explorerRail = (
    <>
      <div className="mb-6">
        <div className="text-sm font-semibold text-slate-200">Sidebar</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500">Configs & retrieval filters</div>
      </div>

      <button
        onClick={onBack}
        className="mb-6 w-full rounded-lg px-3 py-2 text-left text-sm text-blue-400 hover:bg-slate-700/55 hover:text-blue-300 flex items-center gap-1"
      >
        &larr; Back to experiment
      </button>

      {data && (
        <ConfigSidebar
          data={data}
          selectedMethods={selectedMethods}
          onToggleMethod={handleToggleMethod}
        />
      )}
    </>
  );

  return (
    <DashboardShell
      asideWidthClass="w-72"
      contentMaxWidthClass="max-w-6xl"
      header={
        <AppPageChrome
          tone="darkFrame"
          pageTitle="Search explorer"
          pageHint={`Aggregates for experiment ${experimentId.slice(0, 8)}… — ranked configs, optional query filter, and per-hit scores. Sidebar controls retrieval-method visibility.`}
        />
      }
      sidebar={explorerRail}
    >

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {pollWhileRunning && !loading && (
            <div className="mb-4 flex items-center justify-end">
              <PollingIndicator active={isPolling} />
            </div>
          )}

          {loading && (
            <div className="mb-8 flex justify-center">
              <LoadingFeedbackPanel
                title={data ? "Refreshing results…" : "Loading results…"}
                subtitle={
                  data
                    ? "Re-fetching explorer data (query filter changed or refresh triggered)."
                    : "Explorer builds ranked configs plus detailed hits from Mongo — response can be megabytes."
                }
                footer="Shows byte progress once headers arrive (Content-Length yields a %) or an indeterminate bar until then."
                feed={feed}
                receivedBytes={receivedBytes}
                totalBytes={totalBytes}
                theme="light"
              />
            </div>
          )}

          {/* Query selector */}
          {data && data.queries.length > 0 && (
            <div className="mb-6 flex items-center gap-4">
              <div className="flex-1">
                <select
                  value={selectedQuery}
                  onChange={(e) => setSelectedQuery(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 bg-white text-sm text-slate-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All queries ({data.queries.length})</option>
                  {data.queries.map((q) => (
                    <option key={q} value={q}>
                      {q.length > 80 ? q.slice(0, 80) + '...' : q}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex items-center gap-0 mb-6 border-b border-slate-200">
            <button
              onClick={() => setActiveTab('hyperparameters')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'hyperparameters'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Hyperparameters
            </button>
            <button
              onClick={() => setActiveTab('detailed')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'detailed'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Detailed Results
            </button>

            {data && (
              <span className="ml-auto text-xs text-slate-400">
                {filteredResults.length} MATCHES
              </span>
            )}
          </div>

          {loading && data && (
            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50/90 px-4 py-3 text-sm shadow-sm backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-blue-900">Refreshing explorer data…</span>
                <span aria-live="polite" className="font-mono text-xs text-slate-700">
                  {feed.length ? feed[feed.length - 1]?.text.replace(/^—?\s*/, '') : 'waiting…'}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-600">
                <span>
                  {receivedBytes !== null
                    ? `${formatBytes(receivedBytes)}${
                        totalBytes !== null ? ` / ${formatBytes(totalBytes)}` : ' · size unknown'
                      }`
                    : 'Starting request…'}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-blue-100" role="progressbar">
                <div
                  className={`h-full rounded-full bg-sky-500 ${
                    receivedBytes !== null &&
                    totalBytes !== null &&
                    totalBytes > 0 &&
                    receivedBytes <= totalBytes
                      ? 'transition-[width] duration-150'
                      : 'w-2/5 animate-pulse'
                  }`}
                  style={
                    receivedBytes !== null &&
                    totalBytes !== null &&
                    totalBytes > 0 &&
                    receivedBytes <= totalBytes
                      ? {
                          width: `${Math.min(
                            100,
                            Math.max(2, Math.round((100 * receivedBytes) / totalBytes)),
                          )}%`,
                        }
                      : undefined
                  }
                />
              </div>
            </div>
          )}

          {/* Content */}
          {filteredData && activeTab === 'hyperparameters' && (
            <HyperparametersTab data={filteredData} />
          )}

          {filteredData && activeTab === 'detailed' && (
            <DetailedResultsTab results={filteredData.detailed_results} />
          )}

          {!loading && !data && !error && (
            <div className="text-center py-20">
              <div className="mb-4">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
                  <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
              </div>
              <div className="text-lg font-medium text-slate-700 mb-2">Waiting for results</div>
              <div className="text-sm text-slate-500 max-w-md mx-auto">
                {pollWhileRunning
                  ? "The experiment is still running. Results will appear as soon as they're available."
                  : "No explorer data available yet. Try refreshing the experiment detail page."}
              </div>
            </div>
          )}

          {data && data.total_matches === 0 && (
            <div className="text-center py-20 text-slate-400">
              <div className="text-lg mb-2">No results found</div>
              <div className="text-sm">This experiment has no query results stored yet.</div>
            </div>
          )}
    </DashboardShell>
  );
}
