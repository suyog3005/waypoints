'use client';

/**
 * OPUS-5 map shell — RIBBON overlay panels (50% width, right side).
 *
 * Each ribbon tool opens one of these panels over the permanent map:
 *   layers, filters, find, restrictions, legend.
 */

import { useMapStore } from '@/stores/map.store';
import { useOverlayStore } from '@/stores/overlay.store';
import { BLOCKS, TRAINS, RESTRICTIONS, type BlockState } from '@/lib/map-data';
import { getSemantic, LEGEND_ORDER } from '@/lib/palette';
import { SemanticLegend } from '@/components/semantic-badge';
import { X, Search } from 'lucide-react';

function PanelShell({ title, children }: { title: string; children: React.ReactNode }) {
  const close = useOverlayStore((s) => s.close);
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</h2>
        <button type="button" onClick={close} className="rounded p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">{children}</div>
    </div>
  );
}

// ── Layers ─────────────────────────────────────────────────────────────
const LAYER_LABELS: Record<string, string> = {
  baseGraph: 'Lines & stations',
  blocks: 'Blocks (by state)',
  trains: 'Trains',
  restrictions: 'Restrictions',
  conflicts: 'Conflicts',
  traction: 'Traction sections',
  assets: 'Assets',
  labels: 'Labels',
};

export function LayersPanel() {
  const layersVisible = useMapStore((s) => s.layersVisible);
  const setLayerVisible = useMapStore((s) => s.setLayerVisible);
  return (
    <PanelShell title="Layers">
      <div className="space-y-1">
        {Object.entries(LAYER_LABELS).map(([key, label]) => (
          <label key={key} className="flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <span className="text-sm text-slate-700 dark:text-slate-200">{label}</span>
            <input
              type="checkbox"
              checked={layersVisible[key as keyof typeof layersVisible]}
              onChange={(e) => setLayerVisible(key as keyof typeof layersVisible, e.target.checked)}
              className="h-4 w-4 accent-blue-600"
            />
          </label>
        ))}
      </div>
    </PanelShell>
  );
}

// ── Filters ────────────────────────────────────────────────────────────
const BLOCK_STATES: BlockState[] = ['active', 'granted', 'approved', 'requested', 'proposed', 'emergency', 'derived', 'electrically_dead'];

export function FiltersPanel() {
  return (
    <PanelShell title="Filters">
      <div className="space-y-5">
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Block states</h3>
          <div className="flex flex-wrap gap-2">
            {BLOCK_STATES.map((s) => {
              const sem = getSemantic(s);
              return (
                <span key={s} className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs dark:border-slate-700">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: sem.color }} />
                  <span className="text-slate-600 dark:text-slate-300">{sem.label}</span>
                </span>
              );
            })}
          </div>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Train types</h3>
          <div className="flex flex-wrap gap-2">
            <span className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs dark:border-slate-700">
              <span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Passenger
            </span>
            <span className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs dark:border-slate-700">
              <span className="h-2.5 w-2.5 rounded-full bg-green-500" /> Freight
            </span>
            <span className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs dark:border-slate-700">
              <span className="h-2.5 w-2.5 rounded-full border-2 border-red-500" /> Delayed
            </span>
          </div>
        </div>
        <p className="text-xs text-slate-400">
          {BLOCKS.length} blocks · {TRAINS.length} trains · {RESTRICTIONS.length} restrictions on the DLI corridor.
        </p>
      </div>
    </PanelShell>
  );
}

// ── Find ───────────────────────────────────────────────────────────────
export function FindPanel() {
  return (
    <PanelShell title="Find">
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search block, train, or asset…"
          className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
      </div>
      <div className="space-y-1">
        {BLOCKS.slice(0, 8).map((b) => {
          const sem = getSemantic(b.state);
          return (
            <div key={b.id} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: sem.color }} />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{b.id}</span>
                <span className="text-xs text-slate-400">{b.note}</span>
              </div>
              <span className="text-xs tabular-nums text-slate-400">{b.fromKm}–{b.toKm} km</span>
            </div>
          );
        })}
      </div>
    </PanelShell>
  );
}

// ── Restrictions ───────────────────────────────────────────────────────
export function RestrictionsPanel() {
  return (
    <PanelShell title="Restrictions">
      <div className="space-y-2">
        {RESTRICTIONS.map((r) => (
          <div key={r.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{r.id}</span>
              <span className="rounded bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
                {r.speed} km/h
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
              <span>{r.fromKm}–{r.toKm} km</span>
              {r.permanent && <span className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">permanent</span>}
              {r.overdue && <span className="rounded bg-red-100 px-1.5 py-0.5 text-red-600 dark:bg-red-900/40 dark:text-red-300">overdue</span>}
            </div>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}

// ── Legend ─────────────────────────────────────────────────────────────
export function LegendPanel() {
  return (
    <PanelShell title="Legend">
      <SemanticLegend keys={LEGEND_ORDER} />
      <p className="mt-4 text-xs text-slate-400">
        Every block, train, and restriction on the map uses this single semantic
        vocabulary (J2). Colour + pattern are the source of truth — never the
        rendered geometry.
      </p>
    </PanelShell>
  );
}
