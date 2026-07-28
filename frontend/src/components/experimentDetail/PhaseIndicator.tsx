import { Phase } from '../../types';
import { PHASE_ORDER } from './types';

export default function PhaseIndicator({ current }: { current: Phase }) {
  const currentIdx = PHASE_ORDER.indexOf(current);
  const isFailed = current === Phase.FAILED || current === Phase.INTERRUPTED;
  const safeCurrent = typeof current === 'string' ? current : 'unknown';

  return (
    <div className="relative group flex gap-1 items-center">
      {PHASE_ORDER.map((phase, i) => {
        const isCurrent = phase === current;
        const isPast = i < currentIdx;

        let bg = 'bg-slate-200';
        if (isFailed) bg = 'bg-red-300';
        else if (isCurrent) bg = 'bg-blue-500 animate-pulse';
        else if (isPast) bg = 'bg-green-400';

        return (
          <div
            key={phase}
            className={`w-3 h-3 rounded-full ${bg}`}
          />
        );
      })}
      <span className="ml-2 text-xs text-slate-500">{safeCurrent}</span>

      <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 pointer-events-none">
        <div className="bg-slate-800 text-white text-xs rounded-lg shadow-lg px-3 py-2 whitespace-nowrap">
          {PHASE_ORDER.map((p, i) => {
            let icon = '○';
            let color = 'text-slate-400';
            let label = '';
            if (isFailed) {
              icon = '✗';
              color = 'text-red-300';
            } else if (i < currentIdx) {
              icon = '✓';
              color = 'text-green-300';
            } else if (i === currentIdx) {
              icon = '●';
              color = 'text-blue-300';
              label = ' ← current';
            }

            return (
              <div key={p} className={`${color} leading-5`}>
                {icon} {p}{label}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
