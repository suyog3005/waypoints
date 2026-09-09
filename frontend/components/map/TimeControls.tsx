'use client';

import { useTimeStore } from '@/stores/time.store';
import { format } from 'date-fns';
import { RotateCcw, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * TimeControls – time-travel slider and display.
 *
 * Phase 10a.3: Slider (−10 to +50 min, 5 s step), current-time display,
 * reset button. Date/time picker modal deferred to 10a.6.
 */
export function TimeControls() {
  const businessClock = useTimeStore((s) => s.businessClock);
  const timeOffset = useTimeStore((s) => s.timeOffset);
  const setTimeOffset = useTimeStore((s) => s.setTimeOffset);
  const resetToNow = useTimeStore((s) => s.resetToNow);

  const displayTime = new Date(businessClock.getTime() + timeOffset);
  const offsetMin = Math.round(timeOffset / 60_000);

  return (
    <div className="rounded-lg border bg-white/90 p-3 shadow-sm backdrop-blur-sm dark:bg-slate-900/90">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300">
          <Clock className="h-3.5 w-3.5" />
          Time
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-2 text-xs"
          onClick={resetToNow}
          disabled={timeOffset === 0}
        >
          <RotateCcw className="h-3 w-3" />
          Now
        </Button>
      </div>

      {/* Current display time */}
      <p className="mb-2 text-center font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
        {format(displayTime, 'HH:mm:ss')}
      </p>

      {/* Offset slider: −10 min to +50 min, 5 s step */}
      <input
        type="range"
        min={-10 * 60_000}
        max={50 * 60_000}
        step={5_000}
        value={timeOffset}
        onChange={(e) => setTimeOffset(Number(e.target.value))}
        className="w-full accent-blue-600"
        aria-label="Time offset"
      />

      {/* Offset labels */}
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>−10 min</span>
        <span className={offsetMin === 0 ? 'font-semibold text-blue-600' : ''}>
          {offsetMin >= 0 ? '+' : ''}{offsetMin} min
        </span>
        <span>+50 min</span>
      </div>
    </div>
  );
}
