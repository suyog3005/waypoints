/**
 * Map Store - Phase 10a.2
 *
 * Global state for map viewport (zoom, center, extent, selected features)
 * Will be enhanced in Phase 10a.2 with localStorage persistence
 */

import { create } from 'zustand';
import { subscribeWithSelector, persist } from 'zustand/middleware';
import type { ViewMode } from '@/lib/map-data';

export interface MapViewport {
  zoom: number;
  center: { x: number; y: number };
  extent?: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

export interface MapStore {
  // Viewport state
  viewport: MapViewport;
  setZoom: (zoom: number) => void;
  setCenter: (center: { x: number; y: number }) => void;
  setExtent: (extent: MapViewport['extent']) => void;
  resetViewport: () => void;

  // Feature selection
  selectedTrainId: string | null;
  selectedRestrictionId: string | null;
  selectTrain: (id: string | null) => void;
  selectRestriction: (id: string | null) => void;

  // Layer visibility (persisted to localStorage in Phase 10a.2)
  layersVisible: {
    baseGraph: boolean;
    trains: boolean;
    blocks: boolean;
    restrictions: boolean;
    labels: boolean;
    // OPUS-5 Part K layers (off by default, per K2 role defaults).
    traction: boolean;
    assets: boolean;
    conflicts: boolean;
  };
  setLayerVisible: (layer: keyof MapStore['layersVisible'], visible: boolean) => void;

  // OPUS-5 Part K1 — view mode (geographic / schematic / linear).
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

const defaultViewport: MapViewport = {
  zoom: 7,
  center: { x: 80_000, y: 50_000 },  // Center of the expanded grid network (160×100 km)
  extent: undefined,
};

const defaultLayersVisible = {
  baseGraph: true,
  trains: true,
  blocks: true,
  restrictions: true,
  labels: true,
  traction: false,
  assets: false,
  conflicts: true,
};

/**
 * useMapStore - Global map viewport and UI state
 *
 * Persists viewport (zoom, center, extent) and layer visibility to localStorage.
 * Selection state (selectedTrainId, selectedRestrictionId) is NOT persisted
 * (session-specific).
 */
export const useMapStore = create<MapStore>()(
  subscribeWithSelector(
    persist(
      (set) => ({
    // Viewport state
    viewport: defaultViewport,
    setZoom: (zoom) =>
      set((state) => ({
        viewport: { ...state.viewport, zoom },
      })),
    setCenter: (center) =>
      set((state) => ({
        viewport: { ...state.viewport, center },
      })),
    setExtent: (extent) =>
      set((state) => ({
        viewport: { ...state.viewport, extent },
      })),
    resetViewport: () => set({ viewport: defaultViewport }),

    // Feature selection
    selectedTrainId: null,
    selectedRestrictionId: null,
    selectTrain: (id) => set({ selectedTrainId: id }),
    selectRestriction: (id) => set({ selectedRestrictionId: id }),

    // Layer visibility
    layersVisible: defaultLayersVisible,
    setLayerVisible: (layer, visible) =>
      set((state) => ({
        layersVisible: { ...state.layersVisible, [layer]: visible },
      })),

    // OPUS-5 Part K1 — view mode
    viewMode: 'geographic',
    setViewMode: (mode) => set({ viewMode: mode }),
      }),
      {
        name: 'map-store',
        partialize: (state) => ({
          viewport: state.viewport,
          layersVisible: state.layersVisible,
          viewMode: state.viewMode,
        }),
      }
    )
  )
);

// Selectors for efficient re-renders (Phase 10a.5)
export const selectZoom = (state: MapStore) => state.viewport.zoom;
export const selectCenter = (state: MapStore) => state.viewport.center;
export const selectExtent = (state: MapStore) => state.viewport.extent;
export const selectSelectedTrain = (state: MapStore) => state.selectedTrainId;
export const selectLayersVisible = (state: MapStore) => state.layersVisible;
