'use client';

/**
 * OPUS-5 map shell — bottom TIME BAR.
 *
 * A time-offset slider (like the TPS.live reference): scrub from -10 min to
 * +50 min around "now", with a live display and a "Reset to Now" button.
 * Drives the shared time store (used by the polling coordinator / train
 * filtering on the infrastructure map).
 */

import { useTimeStore } from '@/stores/time.store';
import { RotateCcw, Clock } from 'lucide-react';

const MIN_OFFSET = -10 * 60 * 1000; // -10 min
const MAX_OFFSET = 50 * 60 * 1000; // +50 min
const STEP = 5 * 1000; // 5 s

function fmtOffset(ms: number): string {
  const sign = ms < 0 ? '-' : '+';
  const abs = Math.abs(ms);
  const m = Math.floor(abs / 60000);
  const s = Math.floor((abs % 60000) / 1000);
  return `${sign}${m}m ${s.toString().padStart(2, '0')}s`;
}

export function TimeBar() {
  const timeOffset = useTimeStore((s) => s.timeOffset);
  const setTimeOffset = useTimeStore((s) => s.setTimeOffset);
  const resetToNow = useTimeStore((s) => s.resetToNow);
  const displayTime = useTimeStore((s) => s.displayTime);

  const t = displayTime();

  return (
    <div className="flex h-12 shrink-0 items-center gap-4 border-t border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        <Clock className="h-4 w-4" />
        <span className="tabular-nums text-slate-700 dark:text-slate-200">
          {t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 tabular-nums text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          {fmtOffset(timeOffset)}
        </span>
      </div>

      <input
        type="range"
        min={MIN_OFFSET}
        max={MAX_OFFSET}
        step={STEP}
        value={timeOffset}
        onChange={(e) => setTimeOffset(Number(e.target.value))}
        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-200 accent-blue-600 dark:bg-slate-700"
      />

      <button
        type="button"
        onClick={resetToNow}
        className="flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Reset to Now
      </button>
    </div>
  );
}
