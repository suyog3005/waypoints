'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/map.store';
import { TimeControls } from './TimeControls';
import { MapSidebar } from './MapSidebar';

// ── Types ──────────────────────────────────────────────────────────────

export interface BaseGraphNode {
  id: string;
  x: number;
  y: number;
  type: 'station' | 'junction' | 'signal';
  name?: string;
}

export interface BaseGraphEdge {
  id: string;
  from: string;
  to: string;
  trackId?: string;
}

export interface BaseGraphData {
  nodes: BaseGraphNode[];
  edges: BaseGraphEdge[];
}

// ── Coordinate helpers ─────────────────────────────────────────────────

/** 1 degree ≈ 111 320 m at the equator. */
const M = 1 / 111_320;
export const toLon = (x: number) => x * M;
export const toLat = (y: number) => y * M;

// ── Mock base graph (replaced by useBaseGraph in 10a.4) ───────────────

const MOCK_BASE_GRAPH: BaseGraphData = {
  nodes: [
    { id: 'st-a', x: 0, y: 0, type: 'station', name: 'Station A' },
    { id: 'st-b', x: 10_000, y: 0, type: 'station', name: 'Station B' },
    { id: 'st-c', x: 20_000, y: 0, type: 'station', name: 'Station C' },
    { id: 'st-d', x: 30_000, y: 5_000, type: 'station', name: 'Station D' },
    { id: 'st-e', x: 40_000, y: 5_000, type: 'station', name: 'Station E' },
    { id: 'jn-1', x: 15_000, y: 0, type: 'junction' },
    { id: 'jn-2', x: 25_000, y: 2_500, type: 'junction' },
  ],
  edges: [
    { id: 'e-1', from: 'st-a', to: 'jn-1', trackId: 'T1' },
    { id: 'e-2', from: 'jn-1', to: 'st-b', trackId: 'T1' },
    { id: 'e-3', from: 'st-b', to: 'st-c', trackId: 'T2' },
    { id: 'e-4', from: 'st-c', to: 'jn-2', trackId: 'T3' },
    { id: 'e-5', from: 'jn-2', to: 'st-d', trackId: 'T3' },
    { id: 'e-6', from: 'st-d', to: 'st-e', trackId: 'T4' },
  ],
};

// ── Component ──────────────────────────────────────────────────────────

interface MapContainerProps {
  baseGraph?: BaseGraphData;
}

export function MapContainer({ baseGraph = MOCK_BASE_GRAPH }: MapContainerProps) {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const loadedRef = useRef(false);

  const viewport = useMapStore((s) => s.viewport);
  const setZoom = useMapStore((s) => s.setZoom);
  const setCenter = useMapStore((s) => s.setCenter);
  const setExtent = useMapStore((s) => s.setExtent);
  const layersVisible = useMapStore((s) => s.layersVisible);

  // ── Init map (once) ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {},
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': '#f1f5f9' } },
        ],
      },
      center: [toLon(viewport.center.x), toLat(viewport.center.y)],
      zoom: viewport.zoom,
      attributionControl: false,
    });

    mapRef.current = map;

    map.on('move', () => {
      const c = map.getCenter();
      setCenter({ x: c.lng / M, y: c.lat / M });
      setZoom(map.getZoom());
      const b = map.getBounds();
      setExtent({
        minX: b.getWest() / M,
        maxX: b.getEast() / M,
        minY: b.getSouth() / M,
        maxY: b.getNorth() / M,
      });
    });

    map.on('load', () => {
      loadedRef.current = true;
      addBaseGraph(map, baseGraph);
      // TODO 10a.6: addTrainLayers(map), addBlockLayers(map)
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Update base graph on data change ─────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    updateBaseGraph(map, baseGraph);
  }, [baseGraph]);

  // ── Layer visibility ─────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const vis = (v: boolean): 'visible' | 'none' => (v ? 'visible' : 'none');
    const entries: [string, boolean][] = [
      ['base-edges', layersVisible.baseGraph],
      ['base-nodes', layersVisible.baseGraph],
      ['base-labels', layersVisible.labels],
      ['train-cluster', layersVisible.trains],
      ['train-point', layersVisible.trains],
      ['block-segments', layersVisible.blocks],
    ];
    for (const [id, show] of entries) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis(show));
    }
  }, [layersVisible]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute right-3 top-3 z-10">
        <TimeControls />
      </div>
      <div className="absolute bottom-3 left-3 top-3 z-10 w-64 overflow-y-auto">
        <MapSidebar />
      </div>
    </div>
  );
}

// ── Base graph helpers ─────────────────────────────────────────────────

function nodeFeatures(nodes: BaseGraphNode[]) {
  return nodes.map((n) => ({
    type: 'Feature' as const,
    properties: { id: n.id, type: n.type, name: n.name ?? '' },
    geometry: { type: 'Point' as const, coordinates: [toLon(n.x), toLat(n.y)] },
  }));
}

function edgeFeatures(nodes: BaseGraphNode[], edges: BaseGraphEdge[]) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  return edges
    .filter((e) => byId.has(e.from) && byId.has(e.to))
    .map((e) => {
      const a = byId.get(e.from)!;
      const b = byId.get(e.to)!;
      return {
        type: 'Feature' as const,
        properties: { id: e.id, trackId: e.trackId ?? '' },
        geometry: {
          type: 'LineString' as const,
          coordinates: [
            [toLon(a.x), toLat(a.y)],
            [toLon(b.x), toLat(b.y)],
          ],
        },
      };
    });
}

function addBaseGraph(map: maplibregl.Map, data: BaseGraphData) {
  map.addSource('base-nodes', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: nodeFeatures(data.nodes) },
  });
  map.addSource('base-edges', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: edgeFeatures(data.nodes, data.edges) },
  });

  map.addLayer({
    id: 'base-edges',
    type: 'line',
    source: 'base-edges',
    paint: { 'line-color': '#94a3b8', 'line-width': 2 },
  });
  map.addLayer({
    id: 'base-nodes',
    type: 'circle',
    source: 'base-nodes',
    paint: {
      'circle-color': [
        'match',
        ['get', 'type'],
        'station', '#1e40af',
        'junction', '#7c3aed',
        '#64748b',
      ],
      'circle-radius': ['match', ['get', 'type'], 'station', 6, 4],
      'circle-stroke-color': '#fff',
      'circle-stroke-width': 1.5,
    },
  });
  map.addLayer({
    id: 'base-labels',
    type: 'symbol',
    source: 'base-nodes',
    filter: ['==', ['get', 'type'], 'station'],
    layout: {
      'text-field': ['get', 'name'],
      'text-size': 11,
      'text-offset': [0, 1.2],
      'text-anchor': 'top',
    },
    paint: {
      'text-color': '#334155',
      'text-halo-color': '#f1f5f9',
      'text-halo-width': 1.5,
    },
  });
}

function updateBaseGraph(map: maplibregl.Map, data: BaseGraphData) {
  (map.getSource('base-nodes') as maplibregl.GeoJSONSource | undefined)?.setData({
    type: 'FeatureCollection',
    features: nodeFeatures(data.nodes),
  });
  (map.getSource('base-edges') as maplibregl.GeoJSONSource | undefined)?.setData({
    type: 'FeatureCollection',
    features: edgeFeatures(data.nodes, data.edges),
  });
}
