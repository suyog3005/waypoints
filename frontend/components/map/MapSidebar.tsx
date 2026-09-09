'use client';

import { useMapStore } from '@/stores/map.store';
import { useTrains } from '@/lib/hooks';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { TrainFront, Layers } from 'lucide-react';

/**
 * MapSidebar – train list, layer visibility toggles.
 *
 * Phase 10a.3: Layer toggles + train list from useTrains.
 * Phase 10a.6: Restriction list, filter controls.
 */
export function MapSidebar() {
  const layersVisible = useMapStore((s) => s.layersVisible);
  const setLayerVisible = useMapStore((s) => s.setLayerVisible);
  const selectedTrainId = useMapStore((s) => s.selectedTrainId);
  const selectTrain = useMapStore((s) => s.selectTrain);

  const { data: trains, isLoading } = useTrains({ active_only: true });

  return (
    <div className="flex h-full flex-col gap-3 rounded-lg border bg-white/90 p-3 shadow-sm backdrop-blur-sm dark:bg-slate-900/90">
      {/* ── Layer toggles ─────────────────────────────────────────── */}
      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <Layers className="h-3.5 w-3.5" />
          Layers
        </h3>
        <div className="space-y-1.5">
          <LayerToggle
            label="Base Graph"
            checked={layersVisible.baseGraph}
            onChange={(v) => setLayerVisible('baseGraph', v)}
          />
          <LayerToggle
            label="Trains"
            checked={layersVisible.trains}
            onChange={(v) => setLayerVisible('trains', v)}
          />
          <LayerToggle
            label="Blocks"
            checked={layersVisible.blocks}
            onChange={(v) => setLayerVisible('blocks', v)}
          />
          <LayerToggle
            label="Labels"
            checked={layersVisible.labels}
            onChange={(v) => setLayerVisible('labels', v)}
          />
        </div>
      </div>

      <Separator />

      {/* ── Train list ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <TrainFront className="h-3.5 w-3.5" />
          Trains
          {trains && (
            <Badge variant="secondary" className="ml-auto text-[10px]">
              {trains.length}
            </Badge>
          )}
        </h3>

        {isLoading ? (
          <p className="text-xs text-slate-400">Loading…</p>
        ) : trains && trains.length > 0 ? (
          <ul className="space-y-1">
            {trains.map((t) => (
              <li key={t.train_id}>
                <button
                  className={`w-full rounded-md px-2 py-1.5 text-left text-xs transition-colors ${
                    selectedTrainId === t.train_id
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                      : 'text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`}
                  onClick={() => selectTrain(selectedTrainId === t.train_id ? null : t.train_id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{t.train_number}</span>
                    <Badge
                      variant={t.is_active ? 'default' : 'secondary'}
                      className="text-[10px]"
                    >
                      {t.is_active ? 'active' : 'inactive'}
                    </Badge>
                  </div>
                  {t.train_type && (
                    <p className="mt-0.5 text-[10px] text-slate-400">
                      {t.train_type} · {t.schedule_count} schedules
                    </p>
                  )}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-400">No active trains</p>
        )}
      </div>
    </div>
  );
}

// ── Layer toggle row ───────────────────────────────────────────────────

function LayerToggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 rounded accent-blue-600"
      />
      {label}
    </label>
  );
}
