'use client';

/**
 * OPUS-5 — The Map (permanent main content).
 *
 * Layout (per the TPS.live reference + user direction):
 *
 *   ┌──────────────────────────────────────────────────────────┐
 *   │  RIBBON (top) — grouped toolbar, opens 50% overlays      │
 *   ├────┬─────────────────────────────────────────────────────┤
 *   │    │                                                     │
 *   │RAIL│              PERMANENT MAP (PartKMap)               │
 *   │    │              + OVERLAY PANEL (50% or full)          │
 *   │    │                                                     │
 *   ├────┴─────────────────────────────────────────────────────┤
 *   │  TIME BAR (bottom) — time offset slider                  │
 *   └──────────────────────────────────────────────────────────┘
 *
 * The map is always present. Ribbon items open a 50%-width panel on the
 * right; left-rail areas open a full-content panel that covers the map.
 */

import dynamic from 'next/dynamic';
import { Ribbon } from '@/components/map-shell/ribbon';
import { LeftRail } from '@/components/map-shell/left-rail';
import { TimeBar } from '@/components/map-shell/time-bar';
import { OverlayPanel } from '@/components/map-shell/overlay-panel';

const PartKMap = dynamic(() => import('@/components/map/PartKMap').then((m) => m.PartKMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-950 text-sm text-slate-500">
      Loading map…
    </div>
  ),
});

export default function MapShellPage() {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-950">
      <Ribbon />
      <div className="relative flex flex-1 overflow-hidden">
        <LeftRail />
        <div className="relative flex-1">
          <PartKMap />
          <OverlayPanel />
        </div>
      </div>
      <TimeBar />
    </div>
  );
}
