'use client';

/**
 * OPUS-5 map shell — top RIBBON.
 *
 * A grouped toolbar (like the TPS.live reference). Ribbon items open a
 * 50%-width overlay panel over the permanent map. Groups:
 *
 *   Views      — geographic / schematic / linear (K1)
 *   Layers     — toggle Part K layers (K2)
 *   Filters    — filter blocks/trains by state/type
 *   Find       — search a block / train / asset
 *   Restrictions — list & manage restrictions (K4.1)
 *   Legend     — semantic legend (J2)
 */

import { useOverlayStore } from '@/stores/overlay.store';
import { useMapStore } from '@/stores/map.store';
import type { ViewMode } from '@/lib/map-data';
import {
  Map as MapIcon,
  Layers,
  SlidersHorizontal,
  Search,
  ShieldAlert,
  BookOpen,
  type LucideIcon,
} from 'lucide-react';

interface RibbonItem {
  id: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
  onClick?: () => void;
}

interface RibbonGroup {
  title: string;
  items: RibbonItem[];
}

export function Ribbon() {
  const { active, toggle } = useOverlayStore();
  const viewMode = useMapStore((s) => s.viewMode);
  const setViewMode = useMapStore((s) => s.setViewMode);

  const groups: RibbonGroup[] = [
    {
      title: 'Views',
      items: [
        { id: 'view-geo', label: 'Geographic', icon: MapIcon, active: viewMode === 'geographic', onClick: () => setViewMode('geographic' as ViewMode) },
        { id: 'view-schem', label: 'Schematic', icon: MapIcon, active: viewMode === 'schematic', onClick: () => setViewMode('schematic' as ViewMode) },
        { id: 'view-linear', label: 'Linear', icon: MapIcon, active: viewMode === 'linear', onClick: () => setViewMode('linear' as ViewMode) },
      ],
    },
    {
      title: 'Panes',
      items: [
        { id: 'layers', label: 'Layers', icon: Layers, active: active === 'layers', onClick: () => toggle('layers', 'ribbon') },
        { id: 'filters', label: 'Filters', icon: SlidersHorizontal, active: active === 'filters', onClick: () => toggle('filters', 'ribbon') },
        { id: 'find', label: 'Find', icon: Search, active: active === 'find', onClick: () => toggle('find', 'ribbon') },
      ],
    },
    {
      title: 'Inspect',
      items: [
        { id: 'restrictions', label: 'Restrictions', icon: ShieldAlert, active: active === 'restrictions', onClick: () => toggle('restrictions', 'ribbon') },
        { id: 'legend', label: 'Legend', icon: BookOpen, active: active === 'legend', onClick: () => toggle('legend', 'ribbon') },
      ],
    },
  ];

  return (
    <div className="flex h-12 shrink-0 items-stretch gap-1 border-b border-slate-200 bg-white px-2 dark:border-slate-800 dark:bg-slate-900">
      {groups.map((g, gi) => (
        <div key={g.title} className="flex items-stretch">
          {gi > 0 && <div className="mx-1 my-2 w-px bg-slate-200 dark:bg-slate-700" />}
          <div className="flex items-center gap-0.5">
            {g.items.map((it) => (
              <button
                key={it.id}
                type="button"
                onClick={it.onClick}
                title={it.label}
                className={`flex h-9 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors ${
                  it.active
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                }`}
              >
                <it.icon className="h-4 w-4" />
                <span className="hidden lg:inline">{it.label}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
