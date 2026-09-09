'use client';

import { useEffect, useMemo, useRef } from 'react';
import { useMapStore } from '@/stores/map.store';
import { useTileStore } from '@/stores/tile.store';
import { useTimeStore } from '@/stores/time.store';
import { useTrainPositions } from './use-train-positions';
import { getVisibleTiles } from '@/lib/tile-management';
import type { DataTile } from '@/stores/tile.store';

/**
 * usePollingCoordinator – Phase 10a.5
 *
 * Orchestrates the map data pipeline:
 *
 *   viewport extent + display time
 *         │
 *         ▼
 *   getVisibleTiles() → tile IDs
 *         │
 *         ▼
 *   attach cached versions (tile.store)
 *         │
 *         ▼
 *   useTrainPositions(tiles)  ← 2 s refetchInterval
 *         │
 *         ▼
 *   response → update tile version cache + business clock
 *
 * The hook is called once from MapContainer. It reads reactive state from
 * the three Zustand stores and feeds the result into the polling query.
 */
export function usePollingCoordinator() {
  // ── Reactive inputs ──────────────────────────────────────────────────
  const extent = useMapStore((s) => s.viewport.extent);
  const businessClock = useTimeStore((s) => s.businessClock);
  const timeOffset = useTimeStore((s) => s.timeOffset);
  const customTimeEnabled = useTimeStore((s) => s.customTimeEnabled);
  const customTime = useTimeStore((s) => s.customTime);

  // ── Store actions (stable refs) ──────────────────────────────────────
  const setVisibleTiles = useTileStore((s) => s.setVisibleTiles);
  const tileVersionCache = useTileStore((s) => s.tileVersionCache);
  const updateTileVersion = useTileStore((s) => s.updateTileVersion);
  const setBusinessClock = useTimeStore((s) => s.setBusinessClock);

  // ── Compute display time ─────────────────────────────────────────────
  const displayTime = useMemo(() => {
    if (customTimeEnabled && customTime) return customTime;
    return new Date(businessClock.getTime() + timeOffset);
  }, [businessClock, timeOffset, customTimeEnabled, customTime]);

  // ── Compute visible tiles (with cached versions) ─────────────────────
  const tiles: DataTile[] = useMemo(() => {
    if (!extent) return [];
    const tileIds = getVisibleTiles(extent, displayTime);
    return tileIds.map((id) => ({
      id,
      version: tileVersionCache.get(id),
    }));
  }, [extent, displayTime, tileVersionCache]);

  // ── Sync visible tiles into tile.store ───────────────────────────────
  useEffect(() => {
    setVisibleTiles(tiles);
  }, [tiles, setVisibleTiles]);

  // ── Polling query ────────────────────────────────────────────────────
  const { data, isLoading, error } = useTrainPositions({
    tiles,
    enabled: tiles.length > 0,
  });

  // ── Process response: update version cache + business clock ──────────
  const processedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!data) return;

    // Update tile version cache from response meta
    const versions = data.meta?.dataTileVersions;
    if (versions) {
      for (const [tileId, version] of Object.entries(versions)) {
        updateTileVersion(tileId, version);
      }
    }

    // Update business clock from response meta
    if (data.meta?.businessClock) {
      setBusinessClock(new Date(data.meta.businessClock));
    }

    // Track processed data to avoid re-processing on re-render
    processedRef.current = JSON.stringify(data.meta?.dataTileVersions ?? {});
  }, [data, updateTileVersion, setBusinessClock]);

  return {
    /** Filtered train positions for the current display time. */
    positions: data?.positions ?? [],
    /** Whether the polling query is in flight. */
    isLoading,
    /** Error from the last failed fetch (if any). */
    error,
    /** The computed visible tiles (for debugging / UI). */
    visibleTiles: tiles,
    /** The current display time. */
    displayTime,
  };
}
