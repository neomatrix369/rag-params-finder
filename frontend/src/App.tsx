import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { devInfo } from './utils/devLog';
import ExperimentsScreen from './components/screens/ExperimentsScreen';
import ExperimentDetailScreen from './components/screens/ExperimentDetailScreen';
import SearchExplorerScreen from './components/screens/SearchExplorerScreen';
import WalkthruScreen from './components/walkthru/WalkthruScreen';
import { experimentStatsMap } from './components/experiment/experimentList/labels';
import { loadWalkthruResults } from './walkthru/loadWalkthruResults';
import { useWalkthru } from './walkthru/useWalkthru';
import WalkthruOverlay from './walkthru/WalkthruOverlay';
import { WalkthruContext, type WalkthruActions } from './walkthru/WalkthruContext';
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
  | { kind: 'explore'; experimentId: string }
  | { kind: 'walkthru' };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });
  const [listCache, setListCache] = useState<ListCache>({
    experiments: [],
    vectorDbGroups: [],
    ready: false,
  });
  const [detailNav, setDetailNav] = useState<DetailNav>({});

  const walkthruResults = loadWalkthruResults();
  // The screen to return to when the Walkthru exits (it is started from the global About box).
  const returnScreen = useRef<Screen>({ kind: 'list' });

  const walkthru = useWalkthru({
    onExit: () => setScreen(returnScreen.current),
  });

  const startWalkthru = useCallback(() => {
    returnScreen.current = screen.kind === 'walkthru' ? { kind: 'list' } : screen;
    setScreen({ kind: 'walkthru' });
    walkthru.start();
  }, [screen, walkthru]);

  const openDemo = useCallback(() => setScreen({ kind: 'walkthru' }), []);

  const leaveDemo = useCallback(() => {
    if (walkthru.active) walkthru.exit();
    else setScreen({ kind: 'list' });
  }, [walkthru]);

  const walkthruActions = useMemo<WalkthruActions>(
    () => ({ startWalkthru, openDemo, available: true }),
    [startWalkthru, openDemo],
  );

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
    if (screen.kind === 'walkthru') {
      devInfo('App', 'navigate — meetup demo');
      return;
    }
    const id = screen.experimentId.slice(0, 8);
    if (screen.kind === 'detail') {
      devInfo('App', `navigate — experiment detail (${id}…)`);
      return;
    }
    devInfo('App', `navigate — search explorer (${id}…)`);
  }, [screen]);

  const overlay =
    walkthru.active && walkthru.step ? (
      <WalkthruOverlay
        highlight={walkthru.step.highlight}
        stepId={walkthru.step.id}
        title={walkthru.step.title}
        body={walkthru.step.body}
        index={walkthru.index}
        total={walkthru.total}
        paused={walkthru.paused}
        autoplay={walkthru.autoplay}
        isFirst={walkthru.isFirst}
        isLast={walkthru.isLast}
        onNext={walkthru.next}
        onBack={walkthru.back}
        onTogglePause={walkthru.togglePause}
        onSetAutoplay={walkthru.setAutoplay}
        onExit={walkthru.exit}
      />
    ) : null;

  let body: React.ReactNode;
  if (screen.kind === 'walkthru') {
    body = (
      <WalkthruScreen
        results={walkthruResults}
        activeHighlight={walkthru.active ? walkthru.step?.highlight ?? null : null}
        autoplay={walkthru.active && walkthru.autoplay}
        suggestedStore={walkthru.active ? walkthru.step?.choose?.suggest : undefined}
        onBack={leaveDemo}
      />
    );
  } else if (screen.kind === 'explore') {
    body = (
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
  } else if (screen.kind === 'detail') {
    body = (
      <ExperimentDetailScreen
        experimentId={screen.experimentId}
        initialExperiment={screen.initialExperiment ?? detailNav.initialExperiment}
        initialFootprint={screen.initialFootprint ?? detailNav.initialFootprint}
        onBack={() => setScreen({ kind: 'list' })}
        onExplore={() => setScreen({ kind: 'explore', experimentId: screen.experimentId })}
      />
    );
  } else {
    body = (
      <ExperimentsScreen
        cacheReady={listCache.ready}
        cachedExperiments={listCache.ready ? listCache.experiments : undefined}
        cachedVectorDbGroups={listCache.ready ? listCache.vectorDbGroups : undefined}
        onCacheUpdate={handleListCacheUpdate}
        onSelect={openDetail}
      />
    );
  }

  return (
    <WalkthruContext.Provider value={walkthruActions}>
      {body}
      {overlay}
    </WalkthruContext.Provider>
  );
}
