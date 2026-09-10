'use client';

/**
 * OPUS-5 Part K — The Map (self-contained).
 *
 * A permanent map canvas that renders the deterministic DLI corridor network
 * from `lib/map-data.ts` with all Part K layers:
 *
 *   - lines (parallel, K3) + stations
 *   - blocks coloured by semantic state (K4) — the primary layer
 *   - trains coloured by type (K5) — blue passenger / green freight,
 *     red delay ring, hollow if inferred
 *   - restrictions (K4.1) — orange dashed, speed label
 *   - conflicts (K7) — magenta pulsing
 *   - traction sections (K8) — off by default
 *   - assets (K2) — off by default
 *
 * Supports the three view modes (K1): geographic / schematic / linear.
 * All layers re-project when the view mode changes.
 */

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/map.store';
import {
  linesGeoJSON,
  stationsGeoJSON,
  blocksGeoJSON,
  trainsGeoJSON,
  restrictionsGeoJSON,
  conflictsGeoJSON,
  tractionGeoJSON,
  assetsGeoJSON,
  networkBounds,
  type ViewMode,
} from '@/lib/map-data';
import { getSemantic } from '@/lib/palette';

const M = 1 / 111_320;
const toLon = (x: number) => x * M;
const toLat = (y: number) => y * M;

// Semantic state → map colour (from the J2 palette, single source of truth).
const STATE_COLOR: Record<string, string> = {
  active: getSemantic('active').color,
  granted: getSemantic('granted').color,
  approved: getSemantic('approved').color,
  requested: getSemantic('requested').color,
  proposed: getSemantic('proposed').color,
  emergency: getSemantic('emergency').color,
  derived: getSemantic('derived').color,
  electrically_dead: getSemantic('electrically_dead').color,
};

export function PartKMap() {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const loadedRef = useRef(false);
  const viewMode = useMapStore((s) => s.viewMode);
  const layersVisible = useMapStore((s) => s.layersVisible);

  // ── Init map (once) ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
        sources: {},
        layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#0b1220' } }],
      },
      center: [toLon(6000), toLat(0)],
      zoom: 12,
      attributionControl: false,
    });
    mapRef.current = map;

    map.on('load', () => {
      loadedRef.current = true;
      addPartKLayers(map, viewMode);
      fitNetwork(map, viewMode);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Re-project all layers when the view mode changes (K1) ────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    setSource(map, 'lines', linesGeoJSON(viewMode));
    setSource(map, 'stations', stationsGeoJSON(viewMode));
    setSource(map, 'blocks', blocksGeoJSON(viewMode));
    setSource(map, 'trains', trainsGeoJSON(viewMode));
    setSource(map, 'restrictions', restrictionsGeoJSON(viewMode));
    setSource(map, 'conflicts', conflictsGeoJSON(viewMode));
    setSource(map, 'traction', tractionGeoJSON(viewMode));
    setSource(map, 'assets', assetsGeoJSON(viewMode));
    fitNetwork(map, viewMode);
  }, [viewMode]);

  // ── Layer visibility (K2 role defaults) ──────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const vis = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');
    const entries: [string, boolean][] = [
      ['lines', layersVisible.baseGraph],
      ['stations', layersVisible.baseGraph],
      ['station-labels', layersVisible.labels],
      ['blocks', layersVisible.blocks],
      ['trains', layersVisible.trains],
      ['restrictions', layersVisible.restrictions],
      ['conflicts', layersVisible.conflicts],
      ['traction', layersVisible.traction],
      ['assets', layersVisible.assets],
    ];
    for (const [id, show] of entries) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis(show));
    }
  }, [layersVisible]);

  return <div ref={containerRef} className="h-full w-full" />;
}

function setSource(map: maplibregl.Map, id: string, data: any) {
  (map.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData(data);
}

function fitNetwork(map: maplibregl.Map, mode: ViewMode) {
  const b = networkBounds(mode);
  map.fitBounds(
    [
      [toLon(b.minX), toLat(b.minY)],
      [toLon(b.maxX), toLat(b.maxY)],
    ],
    { padding: 60, duration: 400 },
  );
}

// ── Layer definitions ──────────────────────────────────────────────────

function addPartKLayers(map: maplibregl.Map, mode: ViewMode) {
  // Sources
  map.addSource('lines', { type: 'geojson', data: linesGeoJSON(mode) });
  map.addSource('stations', { type: 'geojson', data: stationsGeoJSON(mode) });
  map.addSource('blocks', { type: 'geojson', data: blocksGeoJSON(mode) });
  map.addSource('trains', { type: 'geojson', data: trainsGeoJSON(mode) });
  map.addSource('restrictions', { type: 'geojson', data: restrictionsGeoJSON(mode) });
  map.addSource('conflicts', { type: 'geojson', data: conflictsGeoJSON(mode) });
  map.addSource('traction', { type: 'geojson', data: tractionGeoJSON(mode) });
  map.addSource('assets', { type: 'geojson', data: assetsGeoJSON(mode) });

  // Lines (z=10)
  map.addLayer({
    id: 'lines',
    type: 'line',
    source: 'lines',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': ['get', 'color'],
      'line-width': 3,
      'line-opacity': 0.8,
    },
  });

  // Traction sections (z=15, under blocks) — off by default
  map.addLayer({
    id: 'traction',
    type: 'line',
    source: 'traction',
    layout: { visibility: 'none' },
    paint: {
      'line-color': [
        'match',
        ['get', 'state'],
        'energised', '#16a34a',
        'isolated', '#f59e0b',
        'earthed', '#dc2626',
        '#64748b',
      ],
      'line-width': 8,
      'line-opacity': 0.25,
    },
  });

  // Blocks (z=20) — the primary layer, coloured by semantic state (K4)
  map.addLayer({
    id: 'blocks',
    type: 'line',
    source: 'blocks',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': [
        'match',
        ['get', 'state'],
        'active', STATE_COLOR.active,
        'granted', STATE_COLOR.granted,
        'approved', STATE_COLOR.approved,
        'requested', STATE_COLOR.requested,
        'proposed', STATE_COLOR.proposed,
        'emergency', STATE_COLOR.emergency,
        'derived', STATE_COLOR.derived,
        'electrically_dead', STATE_COLOR.electrically_dead,
        '#64748b',
      ],
      'line-width': 7,
      'line-opacity': 0.9,
      'line-dasharray': [
        'match',
        ['get', 'state'],
        'proposed', 1,
        'requested', 1,
        'derived', 1,
        0,
      ],
    },
  });

  // Restrictions (z=40) — orange dashed, above blocks (K4.1)
  map.addLayer({
    id: 'restrictions',
    type: 'line',
    source: 'restrictions',
    layout: { 'line-join': 'round' },
    paint: {
      'line-color': '#f97316',
      'line-width': 3,
      'line-dasharray': [2, 1.5],
      'line-opacity': 0.95,
    },
  });
  map.addLayer({
    id: 'restriction-labels',
    type: 'symbol',
    source: 'restrictions',
    layout: {
      'text-field': ['concat', ['to-string', ['get', 'speed']], ' km/h'],
      'text-size': 10,
      'text-anchor': 'center',
      'symbol-placement': 'line-center',
    },
    paint: {
      'text-color': '#f97316',
      'text-halo-color': '#0b1220',
      'text-halo-width': 1.5,
    },
  });

  // Stations (z=50)
  map.addLayer({
    id: 'stations',
    type: 'circle',
    source: 'stations',
    paint: {
      'circle-color': '#e2e8f0',
      'circle-radius': 5,
      'circle-stroke-color': '#0b1220',
      'circle-stroke-width': 2,
    },
  });
  map.addLayer({
    id: 'station-labels',
    type: 'symbol',
    source: 'stations',
    layout: {
      'text-field': ['get', 'name'],
      'text-size': 12,
      'text-font': ['Noto Sans Regular'],
      'text-offset': [0, -1.4],
      'text-anchor': 'bottom',
    },
    paint: {
      'text-color': '#f1f5f9',
      'text-halo-color': '#0b1220',
      'text-halo-width': 1.5,
    },
  });

  // Trains (z=60) — coloured by type (K5)
  map.addLayer({
    id: 'trains',
    type: 'circle',
    source: 'trains',
    paint: {
      'circle-color': [
        'match',
        ['get', 'type'],
        'passenger', '#3b82f6',
        'freight', '#22c55e',
        '#64748b',
      ],
      'circle-radius': 6,
      'circle-stroke-color': [
        'case',
        ['get', 'delayed'], '#ef4444',
        '#0b1220',
      ],
      'circle-stroke-width': [
        'case',
        ['get', 'delayed'], 3,
        1.5,
      ],
      'circle-opacity': [
        'case',
        ['get', 'inferred'], 0.4,
        1,
      ],
    },
  });

  // Conflicts (z=70) — magenta pulsing (K7)
  map.addLayer({
    id: 'conflicts',
    type: 'circle',
    source: 'conflicts',
    paint: {
      'circle-color': '#ec4899',
      'circle-radius': 10,
      'circle-stroke-color': '#ec4899',
      'circle-stroke-width': 3,
      'circle-opacity': 0.5,
    },
  });
  map.addLayer({
    id: 'conflict-core',
    type: 'circle',
    source: 'conflicts',
    paint: {
      'circle-color': '#ec4899',
      'circle-radius': 4,
      'circle-stroke-color': '#fff',
      'circle-stroke-width': 1,
    },
  });

  // Assets (z=30) — off by default
  map.addLayer({
    id: 'assets',
    type: 'circle',
    source: 'assets',
    layout: { visibility: 'none' },
    paint: {
      'circle-color': [
        'match',
        ['get', 'condition'],
        'good', '#64748b',
        'watch', '#f59e0b',
        'defective', '#f97316',
        'failed', '#dc2626',
        '#64748b',
      ],
      'circle-radius': 3,
      'circle-stroke-color': '#0b1220',
      'circle-stroke-width': 1,
    },
  });
}
