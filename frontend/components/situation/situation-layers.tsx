"use client";

import { Layers, SlidersHorizontal, RotateCcw } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { useMapStore } from "@/stores/map.store";
import { useTimeStore } from "@/stores/time.store";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J4 — left column: LAYERS, FILTERS, and the TIME slider.
 *
 * The time slider drives everything on the screen simultaneously — map,
 * train graph and the Now panel (J4 key behaviour). This is the most
 * powerful control in the interface.
 */
export function SituationLayers() {
  const layersVisible = useMapStore((s) => s.layersVisible);
  const setLayerVisible = useMapStore((s) => s.setLayerVisible);

  const businessClock = useTimeStore((s) => s.businessClock);
  const timeOffset = useTimeStore((s) => s.timeOffset);
  const setTimeOffset = useTimeStore((s) => s.setTimeOffset);
  const resetToNow = useTimeStore((s) => s.resetToNow);

  const displayTime = new Date(businessClock.getTime() + timeOffset);
  const offsetMin = Math.round(timeOffset / 60_000);
  const isLive = timeOffset === 0;

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto rounded-lg border bg-card p-3">
      {/* Layers */}
      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <Layers className="h-3.5 w-3.5" /> Layers
        </h3>
        <div className="space-y-1.5">
          <LayerRow label="Track" checked={layersVisible.baseGraph} onChange={(v) => setLayerVisible("baseGraph", v)} />
          <LayerRow label="Blocks" checked={layersVisible.blocks} onChange={(v) => setLayerVisible("blocks", v)} />
          <LayerRow label="Restrictions" checked={layersVisible.restrictions} onChange={(v) => setLayerVisible("restrictions", v)} />
          <LayerRow label="Trains" checked={layersVisible.trains} onChange={(v) => setLayerVisible("trains", v)} />
          <LayerRow label="Labels" checked={layersVisible.labels} onChange={(v) => setLayerVisible("labels", v)} />
        </div>
      </div>

      <Separator />

      {/* Filters */}
      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </h3>
        <div className="space-y-1.5 text-xs">
          <FilterSelect label="Dept" value="All" />
          <FilterSelect label="Class" value="All" />
          <FilterSelect label="Status" value="All" />
        </div>
      </div>

      <Separator />

      {/* Time slider */}
      <div>
        <div className="mb-1 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Time</h3>
          <button
            onClick={resetToNow}
            disabled={isLive}
            className={cn(
              "flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium",
              isLive ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" : "text-muted-foreground hover:bg-accent",
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", isLive ? "bg-emerald-500" : "bg-slate-400")} />
            {isLive ? "LIVE" : "Reset"}
          </button>
        </div>
        <p className="mb-1 text-center font-mono text-sm font-semibold">
          {format(displayTime, "HH:mm:ss")}
        </p>
        <input
          type="range"
          min={-6 * 3_600_000}
          max={6 * 3_600_000}
          step={300_000}
          value={timeOffset}
          onChange={(e) => setTimeOffset(Number(e.target.value))}
          className="w-full accent-blue-600"
          aria-label="Time offset"
        />
        <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>−6h</span>
          <span className={cn(isLive && "font-semibold text-emerald-600")}>
            {offsetMin >= 0 ? "+" : ""}{offsetMin} min
          </span>
          <span>+6h</span>
        </div>
        <p className="mt-1 text-center text-[10px] text-muted-foreground">
          {format(displayTime, "d MMM")} · {isLive ? "live" : "time-travel"}
        </p>
      </div>
    </div>
  );
}

function LayerRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-foreground">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 accent-blue-600"
      />
      {label}
    </label>
  );
}

function FilterSelect({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <button className="rounded border px-2 py-0.5 text-[11px] hover:bg-accent">
        {value} ▾
      </button>
    </div>
  );
}
