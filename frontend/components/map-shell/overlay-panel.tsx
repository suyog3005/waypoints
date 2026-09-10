'use client';

/**
 * OPUS-5 map shell — OVERLAY PANEL.
 *
 * Renders the active overlay over the permanent map:
 *   - ribbon items  → 50% width, right side
 *   - sidebar items → full content, covers the map
 *
 * `null` active overlay → renders nothing (map only).
 */

import { useOverlayStore } from '@/stores/overlay.store';
import {
  LayersPanel,
  FiltersPanel,
  FindPanel,
  RestrictionsPanel,
  LegendPanel,
} from './ribbon-panels';
import {
  SituationPanel,
  PlanPanel,
  BlocksPanel,
  ExecutionPanel,
  ResourcesPanel,
  NetworkPanel,
  AnalyticsPanel,
  SettingsPanel,
} from './sidebar-panels';

const RIBBON_PANELS: Record<string, React.ComponentType> = {
  layers: LayersPanel,
  filters: FiltersPanel,
  find: FindPanel,
  restrictions: RestrictionsPanel,
  legend: LegendPanel,
};

const SIDEBAR_PANELS: Record<string, React.ComponentType> = {
  situation: SituationPanel,
  plan: PlanPanel,
  blocks: BlocksPanel,
  execution: ExecutionPanel,
  resources: ResourcesPanel,
  network: NetworkPanel,
  analytics: AnalyticsPanel,
  settings: SettingsPanel,
};

export function OverlayPanel() {
  const { active, kind } = useOverlayStore();
  if (!active || !kind) return null;

  const Panel =
    kind === 'ribbon' ? RIBBON_PANELS[active] : SIDEBAR_PANELS[active];
  if (!Panel) return null;

  // Ribbon → 50% right panel. Sidebar → full content.
  const className =
    kind === 'ribbon'
      ? 'absolute inset-y-0 right-0 z-20 w-1/2 border-l border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900'
      : 'absolute inset-0 z-20 bg-white dark:bg-slate-900';

  return (
    <div className={className}>
      <Panel />
    </div>
  );
}
