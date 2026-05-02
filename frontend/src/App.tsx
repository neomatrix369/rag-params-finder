import { useState } from 'react';
import ExperimentsScreen from './components/ExperimentsScreen';
import ExperimentDetailScreen from './components/ExperimentDetailScreen';
import SearchExplorerScreen from './components/SearchExplorerScreen';

type Screen =
  | { kind: 'list' }
  | { kind: 'detail'; experimentId: string }
  | { kind: 'explore'; experimentId: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: 'list' });

  if (screen.kind === 'explore') {
    return (
      <SearchExplorerScreen
        experimentId={screen.experimentId}
        onBack={() => setScreen({ kind: 'detail', experimentId: screen.experimentId })}
      />
    );
  }

  if (screen.kind === 'detail') {
    return (
      <ExperimentDetailScreen
        experimentId={screen.experimentId}
        onBack={() => setScreen({ kind: 'list' })}
        onExplore={() => setScreen({ kind: 'explore', experimentId: screen.experimentId })}
      />
    );
  }

  return (
    <ExperimentsScreen
      onSelect={(id) => setScreen({ kind: 'detail', experimentId: id })}
    />
  );
}
