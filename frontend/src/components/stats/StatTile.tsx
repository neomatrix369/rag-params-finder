import InfoTip from '../chrome/InfoTip';
import { aboutLabel, explainLabel } from '../chrome/infoTipUtils';

export type StatTileProps = {
  label: string;
  value: string | number;
  /** Short note about the tile; rendered through InfoTip. */
  hint?: string;
  /** How the number is derived. Must come from a pure function, never JSX arithmetic. */
  explain?: string;
  /** `comfortable` for panel tiles; `compact` for dense experiment cards. */
  density?: 'comfortable' | 'compact';
};

function TileTips({ label, hint, explain }: Pick<StatTileProps, 'label' | 'hint' | 'explain'>) {
  return (
    <>
      {hint ? <InfoTip label={aboutLabel(label)}>{hint}</InfoTip> : null}
      {explain ? <InfoTip label={explainLabel(label)}>{explain}</InfoTip> : null}
    </>
  );
}

export default function StatTile({
  label,
  value,
  hint,
  explain,
  density = 'comfortable',
}: StatTileProps) {
  if (density === 'compact') {
    return (
      <div className="rounded-md border border-indigo-100 bg-white/90 px-3 py-2">
        <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          {label}
          <TileTips label={label} hint={hint} explain={explain} />
        </div>
        <div className="text-lg font-bold text-indigo-600">{value}</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-white p-4">
      <div className="mb-1 flex items-center gap-1 text-xs uppercase tracking-wider text-slate-500">
        {label}
        <TileTips label={label} hint={hint} explain={explain} />
      </div>
      <div className="text-2xl font-bold text-indigo-600">{value}</div>
    </div>
  );
}
