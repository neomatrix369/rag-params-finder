import { useCallback, useEffect, useState } from 'react';
import { devInfo } from './utils/devLog';
import ExperimentsScreen from './components/ExperimentsScreen';
import ExperimentDetailScreen from './components/ExperimentDetailScreen';
import SearchExplorerScreen from './components/SearchExplorerScreen';
import type { Experiment, ExperimentDbStatsSummary, VectorDbStatsGroup } from './types';
import { findDbStatsInGroups } from './utils/experimentDbStats';

export type ListCache = {
  experiments: Experiment[];
  vectorDbGroups: VectorDbStatsGroup[];
  ready: boolean;
};

type DetailNav = {
  initialExperiment?: Experiment;
  initialDbStats?: ExperimentDbStatsSummary;
};

type Screen =
  | { kind: 'list' }
  | {
      kind: 'detail';
      experimentId: string;
      initialExperiment?: Experiment;
      initialDbStats?: ExperimentDbStatsSummary;
    }
  | { kind: 'explore'; experimentId: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });
  const [listCache, setListCache] = useState<ListCache>({
    experiments: [],
    vectorDbGroups: [],
    ready: false,
  });
  const [detailNav, setDetailNav] = useState<DetailNav>({});

  const handleListCacheUpdate = useCallback(
    (update: { experiments: Experiment[]; vectorDbGroups: VectorDbStatsGroup[] }) => {
      setListCache((prev) => ({
        ...prev,
        experiments: update.experiments,
        vectorDbGroups: update.vectorDbGroups,
        ready: true,
      }));
    },
    [],
  );

  const openDetail = useCallback(
    (experiment: Experiment) => {
      const initialDbStats = findDbStatsInGroups(listCache.vectorDbGroups, experiment.experiment_id);
      const nav: DetailNav = { initialExperiment: experiment, initialDbStats };
      setDetailNav(nav);
      setScreen({
        kind: 'detail',
        experimentId: experiment.experiment_id,
        initialExperiment: experiment,
        initialDbStats,
      });
    },
    [listCache.vectorDbGroups],
  );

  useEffect(() => {
    if (screen.kind === 'list') {
      devInfo('App', 'navigate — experiments list');
      return;
    }
    const id = screen.experimentId.slice(0, 8);
    if (screen.kind === 'detail') {
      devInfo('App', `navigate — experiment detail (${id}…)`);
      return;
    }
    devInfo('App', `navigate — search explorer (${id}…)`);
  }, [screen]);

  if (screen.kind === 'explore') {
    return (
      <SearchExplorerScreen
        experimentId={screen.experimentId}
        onBack={() =>
          setScreen({
            kind: 'detail',
            experimentId: screen.experimentId,
            initialExperiment: detailNav.initialExperiment,
            initialDbStats: detailNav.initialDbStats,
          })
        }
      />
    );
  }

  if (screen.kind === 'detail') {
    return (
      <ExperimentDetailScreen
        experimentId={screen.experimentId}
        initialExperiment={screen.initialExperiment ?? detailNav.initialExperiment}
        initialDbStats={screen.initialDbStats ?? detailNav.initialDbStats}
        onBack={() => setScreen({ kind: 'list' })}
        onExplore={() => setScreen({ kind: 'explore', experimentId: screen.experimentId })}
      />
    );
  }

  return (
    <ExperimentsScreen
      cacheReady={listCache.ready}
      cachedExperiments={listCache.ready ? listCache.experiments : undefined}
      cachedVectorDbGroups={listCache.ready ? listCache.vectorDbGroups : undefined}
      onCacheUpdate={handleListCacheUpdate}
      onSelect={openDetail}
    />
  );
}
