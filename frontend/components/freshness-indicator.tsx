'use client';

import { Clock } from 'lucide-react';
import { formatDateTime, relativeTime } from '@/lib/format';

export function FreshnessIndicator({ syncedAt }: { syncedAt: string }) {
  const now = new Date();
  const lastSync = new Date(syncedAt);
  const isStale = now.getTime() - lastSync.getTime() > 60000; // > 1 minute

  return (
    <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-md ${
      isStale ? 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-200' : 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-200'
    }`}>
      <Clock className="h-3 w-3" />
      <span>Last synced {relativeTime(syncedAt)}</span>
      <span className="text-xs opacity-70">({formatDateTime(syncedAt)})</span>
    </div>
  );
}
