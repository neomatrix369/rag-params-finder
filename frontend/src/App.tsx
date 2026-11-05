import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { devInfo } from './utils/devLog';
import ExperimentsScreen from './components/screens/ExperimentsScreen';
import ExperimentDetailScreen from './components/screens/ExperimentDetailScreen';
import CompareScreen from './components/screens/CompareScreen';
import SearchExplorerScreen from './components/screens/SearchExplorerScreen';
import WalkthruScreen from './components/walkthru/WalkthruScreen';
import { loadWalkthruResults } from './walkthru/loadWalkthruResults';
import { useWalkthru } from './walkthru/useWalkthru';
import WalkthruOverlay from './walkthru/WalkthruOverlay';
import { WalkthruContext, type WalkthruActions } from './walkthru/WalkthruContext';
import type { Experiment } from './types';

export type ListCache = {
  experiments: Experiment[];
  ready: boolean;
};

type DetailNav = {
  initialExperiment?: Experiment;
};

type Screen =
  | { kind: 'list' }
  | {
      kind: 'detail';
      experimentId: string;
      initialExperiment?: Experiment;
    }
  | { kind: 'explore'; experimentId: string }
  | { kind: 'walkthru' }
  | { kind: 'compare' };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });
  const [listCache, setListCache] = useState<ListCache>({
    experiments: [],
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
    (update: { experiments: Experiment[] }) => {
      setListCache((prev) => ({
        ...prev,
        experiments: update.experiments,
        ready: true,
      }));
    },
    [],
  );

  const openDetail = useCallback(
    (experiment: Experiment) => {
      const nav: DetailNav = { initialExperiment: experiment };
      setDetailNav(nav);
      setScreen({
        kind: 'detail',
        experimentId: experiment.experiment_id,
        initialExperiment: experiment,
      });
    },
    [],
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
    if (screen.kind === 'compare') {
      devInfo('App', 'navigate — compare sweeps');
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
        onExit={walkthru.exit}
      />
    ) : null;

  let body: React.ReactNode;
  if (screen.kind === 'walkthru') {
    body = (
      <WalkthruScreen
        results={walkthruResults}
        activeHighlight={walkthru.active ? walkthru.step?.highlight ?? null : null}
        autoplay={walkthru.active}
        suggestedStore={walkthru.active ? walkthru.step?.choose?.suggest : undefined}
        onBack={leaveDemo}
      />
    );
  } else if (screen.kind === 'compare') {
    body = <CompareScreen onBack={() => setScreen({ kind: 'list' })} />;
  } else if (screen.kind === 'explore') {
    body = (
      <SearchExplorerScreen
        experimentId={screen.experimentId}
        onBack={() =>
          setScreen({
            kind: 'detail',
            experimentId: screen.experimentId,
            initialExperiment: detailNav.initialExperiment,
          })
        }
      />
    );
  } else if (screen.kind === 'detail') {
    body = (
      <ExperimentDetailScreen
        experimentId={screen.experimentId}
        initialExperiment={screen.initialExperiment ?? detailNav.initialExperiment}
        onBack={() => setScreen({ kind: 'list' })}
        onExplore={() => setScreen({ kind: 'explore', experimentId: screen.experimentId })}
      />
    );
  } else {
    body = (
      <ExperimentsScreen
        cacheReady={listCache.ready}
        cachedExperiments={listCache.ready ? listCache.experiments : undefined}
        onCacheUpdate={handleListCacheUpdate}
        onSelect={openDetail}
        onCompare={() => setScreen({ kind: 'compare' })}
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
