import { useState } from 'react';
import ExperimentsScreen from './components/ExperimentsScreen';
import ExperimentDetailScreen from './components/ExperimentDetailScreen';

export default function App() {
  const [selectedExperiment, setSelectedExperiment] = useState<string | null>(null);

  if (selectedExperiment) {
    return (
      <ExperimentDetailScreen
        experimentId={selectedExperiment}
        onBack={() => setSelectedExperiment(null)}
      />
    );
  }

  return <ExperimentsScreen onSelect={setSelectedExperiment} />;
}
