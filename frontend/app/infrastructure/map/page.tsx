'use client';

import { Suspense } from 'react';
import { MapContainer } from '@/components/map/MapContainer';

/**
 * Map Page – Phase 10a.3
 *
 * Renders the railway infrastructure map with train positions,
 * block overlays, time controls, and a sidebar.
 */
export default function MapPage() {
  return (
    <div className="h-screen w-full bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <Suspense fallback={<MapLoading />}>
        <MapContainer />
      </Suspense>
    </div>
  );
}

function MapLoading() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="text-center">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900 dark:border-slate-800 dark:border-t-slate-50" />
        <p className="text-slate-600 dark:text-slate-400">Loading map…</p>
      </div>
    </div>
  );
}
