import { useCallback, useEffect, useState } from 'react';
import { devInfo } from './utils/devLog';
import ExperimentsScreen from './components/screens/ExperimentsScreen';
import ExperimentDetailScreen from './components/screens/ExperimentDetailScreen';
import SearchExplorerScreen from './components/screens/SearchExplorerScreen';
import { experimentStatsMap } from './components/experiment/experimentList/labels';
import type { Experiment, ExperimentDbStats, VectorDbStatsGroup } from './types';

export type ListCache = {
  experiments: Experiment[];
  vectorDbGroups: VectorDbStatsGroup[];
  ready: boolean;
};

type DetailNav = {
  initialExperiment?: Experiment;
  initialFootprint?: ExperimentDbStats;
};

type Screen =
  | { kind: 'list' }
  | {
      kind: 'detail';
      experimentId: string;
      initialExperiment?: Experiment;
      initialFootprint?: ExperimentDbStats;
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
      const initialFootprint = experimentStatsMap(listCache.vectorDbGroups).get(experiment.experiment_id);
      const nav: DetailNav = { initialExperiment: experiment, initialFootprint };
      setDetailNav(nav);
      setScreen({
        kind: 'detail',
        experimentId: experiment.experiment_id,
        initialExperiment: experiment,
        initialFootprint,
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
            initialFootprint: detailNav.initialFootprint,
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
        initialFootprint={screen.initialFootprint ?? detailNav.initialFootprint}
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
