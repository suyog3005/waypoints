'use client';

/**
 * OPUS-5 map shell — left RAIL.
 *
 * A slim vertical icon rail. Each item is a Part J "area" (Plan, Blocks,
 * Demands, Execution, Analytics, …). Clicking one opens a FULL-content
 * overlay that covers the map (unlike ribbon items, which open 50% panels).
 */

import { useOverlayStore } from '@/stores/overlay.store';
import {
  LayoutDashboard,
  CalendarRange,
  Inbox,
  PlayCircle,
  Wrench,
  Network,
  BarChart3,
  Settings,
  type LucideIcon,
} from 'lucide-react';

interface RailItem {
  id: string;
  label: string;
  icon: LucideIcon;
}

const ITEMS: RailItem[] = [
  { id: 'situation', label: 'Situation', icon: LayoutDashboard },
  { id: 'plan', label: 'Plan', icon: CalendarRange },
  { id: 'blocks', label: 'Blocks', icon: Inbox },
  { id: 'execution', label: 'Execution', icon: PlayCircle },
  { id: 'resources', label: 'Resources', icon: Wrench },
  { id: 'network', label: 'Network', icon: Network },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function LeftRail() {
  const { active, toggle } = useOverlayStore();

  return (
    <div className="flex w-14 shrink-0 flex-col items-center gap-1 border-r border-slate-200 bg-white py-2 dark:border-slate-800 dark:bg-slate-900">
      {ITEMS.map((it) => (
        <button
          key={it.id}
          type="button"
          onClick={() => toggle(it.id, 'sidebar')}
          title={it.label}
          className={`flex h-11 w-11 flex-col items-center justify-center gap-0.5 rounded-lg transition-colors ${
            active === it.id
              ? 'bg-blue-600 text-white'
              : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
          }`}
        >
          <it.icon className="h-5 w-5" />
        </button>
      ))}
    </div>
  );
}
