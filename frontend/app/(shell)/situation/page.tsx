"use client";

import dynamic from "next/dynamic";
import { SituationLayers } from "@/components/situation/situation-layers";
import { NowPanel } from "@/components/situation/now-panel";
import { TrainGraph } from "@/components/situation/train-graph";

/**
 * OPUS-5 Part J4 — the Situation screen (the landing page).
 *
 * Layout:
 *   ┌───────────┬──────────────────────────────┬───────────┐
 *   │ LAYERS    │                              │   NOW     │
 *   │ FILTERS   │        [ MAP CANVAS ]        │           │
 *   │ TIME      │                              │           │
 *   ├───────────┴──────────────────────────────┴───────────┤
 *   │ TRAIN GRAPH (collapsible time–distance chart)         │
 *   └───────────────────────────────────────────────────────┘
 *
 * The time slider (left) drives the map, the train graph and the Now panel
 * simultaneously. MapContainer is loaded client-only (ssr: false) for the
 * same hydration reasons as the standalone map page.
 */
const MapContainer = dynamic(
  () => import("@/components/map/MapContainer").then((m) => m.MapContainer),
  { ssr: false, loading: () => <MapLoading /> },
);

export default function SituationPage() {
  return (
    <div className="flex h-[calc(100vh-5.5rem)] flex-col gap-3">
      {/* Main row: layers | map | now */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-[16rem_1fr_18rem]">
        <div className="hidden min-h-0 lg:block">
          <SituationLayers />
        </div>

        <div className="min-h-0 overflow-hidden rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
          <MapContainer />
        </div>

        <div className="min-h-0">
          <NowPanel />
        </div>
      </div>

      {/* Train graph (collapsible) */}
      <div className="shrink-0">
        <TrainGraph />
      </div>
    </div>
  );
}

function MapLoading() {
  return (
    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="text-center">
        <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900 dark:border-slate-800 dark:border-t-slate-50" />
        <p className="text-sm text-slate-600 dark:text-slate-400">Loading map…</p>
      </div>
    </div>
  );
}
