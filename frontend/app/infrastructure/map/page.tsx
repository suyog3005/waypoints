'use client';

import { Suspense } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Map Page - Phase 10a.1 Scaffolding
 * 
 * Shows the railway infrastructure map with train positions, blocks, and time controls.
 * Components will be added in phases 10a.2-10a.7
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

/**
 * MapContainer - Main map rendering component
 * Will be moved to components/map/MapContainer.tsx in 10a.3
 */
function MapContainer() {
  return (
    <div className="flex h-full w-full gap-4 p-4">
      {/* Sidebar - will be MapSidebar component in 10a.3 */}
      <div className="w-64 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-50">Map Controls</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">Phase 10a.1: Infrastructure scaffolding</p>
          </div>
          
          {/* Placeholder for TimeControls component (10a.3) */}
          <div className="space-y-2 border-t border-slate-200 dark:border-slate-800 pt-4">
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">Time Controls</h4>
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>

          {/* Placeholder for train list (10a.3) */}
          <div className="space-y-2 border-t border-slate-200 dark:border-slate-800 pt-4">
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300">Trains</h4>
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>
        </div>
      </div>

      {/* Main map area - will be MapContainer component in 10a.3 */}
      <div className="flex-1 rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <div className="mb-4 text-4xl">🗺️</div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Map Container</h2>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              Maplibre GL will render here
            </p>
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              Phase 10a.3: MapContainer component (stores, layers, polling)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * MapLoading - Fallback while map is loading
 */
function MapLoading() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="text-center">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900 dark:border-slate-800 dark:border-t-slate-50" />
        <p className="text-slate-600 dark:text-slate-400">Loading map...</p>
      </div>
    </div>
  );
}
