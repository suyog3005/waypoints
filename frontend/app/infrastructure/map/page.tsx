'use client';

import dynamic from 'next/dynamic';

/**
 * Map Page – Phase 10a.3
 *
 * Renders the railway infrastructure map with train positions,
 * block overlays, time controls, and a sidebar.
 *
 * MapContainer is loaded client-only (ssr: false). It reads live clock
 * state (businessClock) and initializes a Maplibre GL instance tied to a
 * DOM container ref — both are fundamentally client-only concerns. SSR-ing
 * it caused a time-text hydration mismatch (server-rendered clock value vs.
 * client Date.now()), which made React discard/remount the DOM subtree
 * after hydration. MapContainer's map-init effect has a
 * `mapRef.current` guard (so it doesn't recreate the map on every render),
 * so the remount orphaned the Maplibre canvas against a detached container,
 * leaving the map area blank. Disabling SSR for this component avoids the
 * mismatch entirely.
 */
const MapContainer = dynamic(
  () => import('@/components/map/MapContainer').then((m) => m.MapContainer),
  { ssr: false, loading: () => <MapLoading /> },
);

export default function MapPage() {
  return (
    <div className="h-[calc(100vh-5.5rem)] w-full overflow-hidden rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <MapContainer />
    </div>
  );
}

function MapLoading() {
  return (
    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="text-center">
        <div className="mb-4 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900 dark:border-slate-800 dark:border-t-slate-50" />
        <p className="text-slate-600 dark:text-slate-400">Loading map…</p>
      </div>
    </div>
  );
}
