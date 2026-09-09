/**
 * Tile Store - Phase 10a.2
 * 
 * Tracks visible tiles and cached tile versions for delta transfer optimization
 * Will be populated in Phase 10a.5 (polling loop)
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface DataTile {
  id: string; // Format: "{x}_{y}_{timestamp}"
  version?: string; // UUID - optional when polling
}

export interface TileStore {
  // Visible tiles for current viewport + time window
  visibleTiles: DataTile[];
  setVisibleTiles: (tiles: DataTile[]) => void;

  // Cache of tile versions (for delta transfer)
  // Map of tileId -> UUID version
  tileVersionCache: Map<string, string>;
  updateTileVersion: (tileId: string, version: string) => void;
  clearVersionCache: () => void;

  // Loading state for polling coordinator
  isLoading: boolean;
  setLoading: (loading: boolean) => void;

  // Track failed tiles for retry logic
  failedTiles: Set<string>;
  addFailedTile: (tileId: string) => void;
  clearFailedTiles: () => void;
}

/**
 * useTileStore - Tile visibility and caching state
 * 
 * Populated by:
 * - Phase 10a.5: Viewport change -> recalculate tiles -> update visibleTiles
 * - Phase 10a.5: API response -> update tileVersionCache
 * 
 * Used by:
 * - Phase 10a.5: Polling coordinator (reads visibleTiles, tileVersionCache)
 * - Phase 10a.6: Map layers (reads visibleTiles)
 */
export const useTileStore = create<TileStore>()(
  subscribeWithSelector((set) => ({
    // Visible tiles
    visibleTiles: [],
    setVisibleTiles: (tiles) => set({ visibleTiles: tiles }),

    // Tile version cache (prevents re-fetching unchanged tiles)
    tileVersionCache: new Map(),
    updateTileVersion: (tileId, version) =>
      set((state) => {
        const newCache = new Map(state.tileVersionCache);
        newCache.set(tileId, version);
        return { tileVersionCache: newCache };
      }),
    clearVersionCache: () => set({ tileVersionCache: new Map() }),

    // Loading state
    isLoading: false,
    setLoading: (loading) => set({ isLoading: loading }),

    // Failed tiles for retry logic
    failedTiles: new Set(),
    addFailedTile: (tileId) =>
      set((state) => {
        const newFailed = new Set(state.failedTiles);
        newFailed.add(tileId);
        return { failedTiles: newFailed };
      }),
    clearFailedTiles: () => set({ failedTiles: new Set() }),
  }))
);

// Selectors for efficient re-renders (Phase 10a.5)
export const selectVisibleTiles = (state: TileStore) => state.visibleTiles;
export const selectTileVersionCache = (state: TileStore) => state.tileVersionCache;
export const selectTileLoading = (state: TileStore) => state.isLoading;
