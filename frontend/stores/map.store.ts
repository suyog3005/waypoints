/**
 * Map Store - Phase 10a.2
 *
 * Global state for map viewport (zoom, center, extent, selected features)
 * Will be enhanced in Phase 10a.2 with localStorage persistence
 */

import { create } from 'zustand';
import { subscribeWithSelector, persist } from 'zustand/middleware';

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
  };
  setLayerVisible: (layer: keyof MapStore['layersVisible'], visible: boolean) => void;
}

const defaultViewport: MapViewport = {
  zoom: 10,
  center: { x: 0, y: 0 },
  extent: undefined,
};

const defaultLayersVisible = {
  baseGraph: true,
  trains: true,
  blocks: true,
  restrictions: true,
  labels: true,
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
      }),
      {
        name: 'map-store',
        partialize: (state) => ({
          viewport: state.viewport,
          layersVisible: state.layersVisible,
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
