'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useMapStore } from '@/stores/map.store';
import { useTileStore } from '@/stores/tile.store';
import { useTimeStore } from '@/stores/time.store';
import { useTrainPositions } from './use-train-positions';
import { getVisibleTiles } from '@/lib/tile-management';
import type { DataTile } from '@/stores/tile.store';
import type { TrainPosition } from '@/components/map/TrainLayer';

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
  // ── Per-tile position cache (delta transfer) ─────────────────────────
  // The backend returns positions grouped by tile, and only for tiles whose
  // version changed. We keep a per-tile cache so unchanged tiles retain their
  // positions across polls (a flat response would wipe them out).
  const tilePositionsRef = useRef<Map<string, TrainPosition[]>>(new Map());
  const [mergedPositions, setMergedPositions] = useState<TrainPosition[]>([]);

  // Keep the latest visible tile IDs in a ref so the merge effect below does
  // NOT depend on `tiles` (whose identity changes whenever the version cache
  // updates — depending on it would cause an infinite re-render loop).
  const visibleIdsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    visibleIdsRef.current = new Set(tiles.map((t) => t.id));
  }, [tiles]);

  useEffect(() => {
    if (!data) return;

    // Merge the delta: replace cached positions for each changed tile.
    const cache = tilePositionsRef.current;
    const visibleIds = visibleIdsRef.current;
    for (const [tileId, positions] of Object.entries(data.tiles)) {
      cache.set(tileId, positions);
    }
    // Prune tiles that are no longer visible (re-fetched when viewport returns).
    for (const id of Array.from(cache.keys())) {
      if (!visibleIds.has(id)) cache.delete(id);
    }

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

    // Flatten the per-tile cache into the position list the map renders.
    const merged: TrainPosition[] = [];
    for (const positions of cache.values()) merged.push(...positions);
    setMergedPositions(merged);
  }, [data, updateTileVersion, setBusinessClock]);

  return {
    /** Merged train positions (all visible tiles) for the current display time. */
    positions: mergedPositions,
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
