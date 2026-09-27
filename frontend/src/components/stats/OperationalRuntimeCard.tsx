import { useEffect, useState } from 'react';
import CollapsibleCard from '../chrome/CollapsibleCard';
import { getStorageHealth, type StoreHealthProbe, type StorageHealth } from '../../services/apiClient';
import StatRow from './StatRow';

type OperationalRuntimeCardProps = {
  experimentId: string;
};

function probeStatus(probe: StoreHealthProbe): string {
  return probe.ok ? 'reachable' : 'unreachable';
}

function StoreProbePanel({ title, probe }: { title: string; probe: StoreHealthProbe }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{title}</p>
      <StatRow label="Backend" value={probe.provider} />
      <StatRow label="Mode" value={probe.mode} mono />
      <StatRow label="Status" value={probeStatus(probe)} />
      <StatRow label="Container" value={probe.container ?? '—'} mono />
      <StatRow label="Image" value={probe.image ?? '—'} mono />
    </div>
  );
}

export default function OperationalRuntimeCard({ experimentId }: OperationalRuntimeCardProps) {
  const [health, setHealth] = useState<StorageHealth | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getStorageHealth(controller.signal)
      .then((body) => {
        setHealth(body);
        setFailed(false);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setFailed(true);
      });
    return () => controller.abort();
  }, []);

  const headerExtra = health ? (
    <span className="max-w-[14rem] truncate text-xs font-semibold text-indigo-700">
      {health.stores.vector.mode} · {health.stores.run_state.mode}
    </span>
  ) : null;

  return (
    <div className="mb-4 rounded-lg border border-indigo-100 bg-white px-4 py-3">
      <CollapsibleCard
        title="Store runtime"
        compact
        defaultOpen={false}
        storageKey={`exp-store-runtime-${experimentId}`}
        headerExtra={headerExtra}
      >
        <p className="mb-3 text-xs text-slate-500">
          Vector store and run-state backend for this server. Local modes include the Compose container and image.
        </p>
        {failed && health === null ? (
          <p className="text-sm text-slate-500">Store runtime is unavailable.</p>
        ) : health === null ? (
          <p className="text-sm text-slate-600">Loading store runtime…</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <StoreProbePanel title="Vector store" probe={health.stores.vector} />
            <StoreProbePanel title="Run state" probe={health.stores.run_state} />
          </div>
        )}
      </CollapsibleCard>
    </div>
  );
}
