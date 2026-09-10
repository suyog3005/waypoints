'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMapStore } from '@/stores/map.store';
import { useBaseGraph } from '@/lib/hooks/use-base-graph';
import { usePollingCoordinator } from '@/lib/hooks/use-polling-coordinator';
import { trainPositionsToGeoJSON, filterByTime } from './TrainLayer';
import { deriveBlocks, blocksToGeoJSON } from './BlockLayer';
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

export interface BaseGraphWaypoint {
  x: number;
  y: number;
}

export interface BaseGraphEdge {
  id: string;
  from: string;
  to: string;
  trackId?: string;
  waypoints?: BaseGraphWaypoint[];
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
    // Edge with curved waypoints for visual demo
    {
      id: 'e-4',
      from: 'st-c',
      to: 'jn-2',
      trackId: 'T3',
      waypoints: [
        { x: 22_000, y: 1_200 },  // Slight upward curve
        { x: 24_000, y: 1_800 },  // Gradual bend
      ],
    },
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
  const graphRef = useRef<BaseGraphData>(baseGraph);

  const viewport = useMapStore((s) => s.viewport);
  const setZoom = useMapStore((s) => s.setZoom);
  const setCenter = useMapStore((s) => s.setCenter);
  const setExtent = useMapStore((s) => s.setExtent);
  const resetViewport = useMapStore((s) => s.resetViewport);
  const layersVisible = useMapStore((s) => s.layersVisible);

  // ── Data hooks (Phase 10a.4 / 10a.5) ─────────────────────────────────
  // Base graph: prefer live data, fall back to mock while loading/error.
  const { data: liveBaseGraph } = useBaseGraph();
  const graph = liveBaseGraph ?? baseGraph;

  // Polling coordinator: computes visible tiles + polls train positions.
  const { positions, isLoading: trainsLoading, displayTime } = usePollingCoordinator();

  // Keep a ref to the latest graph so imperative handlers (fitToNetwork,
  // 'load' callback) always see current data without re-registering.
  graphRef.current = graph;

  /**
   * Fit the camera to the base-graph's bounding box (with padding).
   *
   * Guards against the "blank map" failure mode: because viewport
   * (zoom/center) is persisted to localStorage (Phase 10a.2), a user who
   * pans/zooms away from the network — or a stale/corrupted persisted
   * value — leaves the map looking at empty space on next load, with no
   * visual cue that data exists elsewhere. This recenters/rescales to
   * guarantee the whole network is always reachable in one click.
   */
  const fitToNetwork = () => {
    const map = mapRef.current;
    const nodes = graphRef.current.nodes;
    if (!map || nodes.length === 0) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    }
    map.fitBounds(
      [
        [toLon(minX), toLat(minY)],
        [toLon(maxX), toLat(maxY)],
      ],
      { padding: 48, duration: 0 },
    );
  };

  // ── Init map (once) ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        // Glyphs required for symbol (text) layers: station labels + cluster counts.
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
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
      addBaseGraph(map, graphRef.current);
      addTrainLayers(map);
      addBlockLayers(map);
      addRestrictionLayers(map);
      wireMapInteractions(map);

      // Self-heal a stale/out-of-bounds persisted viewport (see fitToNetwork
      // doc comment): if the initial center sits far outside the network's
      // bounding box, snap to a view that fits the whole network instead of
      // rendering an empty viewport with no visual explanation.
      const nodes = graphRef.current.nodes;
      if (nodes.length > 0) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const n of nodes) {
          if (n.x < minX) minX = n.x;
          if (n.x > maxX) maxX = n.x;
          if (n.y < minY) minY = n.y;
          if (n.y > maxY) maxY = n.y;
        }
        const marginX = (maxX - minX) * 0.5 || 10_000;
        const marginY = (maxY - minY) * 0.5 || 10_000;
        const { x, y } = viewport.center;
        const outOfBounds =
          x < minX - marginX || x > maxX + marginX || y < minY - marginY || y > maxY + marginY;
        if (outOfBounds) fitToNetwork();
      }
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
    updateBaseGraph(map, graph);
  }, [graph]);

  // ── Update train positions (Phase 10a.5) ─────────────────────────────
  // Filter by display time, then push into the train GeoJSON source.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const active = filterByTime(positions, displayTime);
    (map.getSource('trains') as maplibregl.GeoJSONSource | undefined)?.setData(
      trainPositionsToGeoJSON(active),
    );
  }, [positions, displayTime]);

  // ── Update block occupancy (derived from train positions) ────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const active = filterByTime(positions, displayTime);
    const blocks = deriveBlocks(active);
    (map.getSource('blocks') as maplibregl.GeoJSONSource | undefined)?.setData(
      blocksToGeoJSON(blocks),
    );
  }, [positions, displayTime]);

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
      ['train-cluster-count', layersVisible.trains],
      ['train-point', layersVisible.trains],
      ['block-segments', layersVisible.blocks],
      ['restriction-segments', layersVisible.restrictions],
    ];
    for (const [id, show] of entries) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis(show));
    }
  }, [layersVisible]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute right-3 top-3 z-10 flex flex-col items-end gap-2">
        <TimeControls />
        <button
          type="button"
          onClick={() => {
            resetViewport();
            fitToNetwork();
          }}
          className="rounded-lg border bg-white/90 px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm backdrop-blur-sm hover:bg-white dark:bg-slate-900/90 dark:text-slate-300 dark:hover:bg-slate-900"
          title="Recenter the map to show the entire network"
        >
          Fit Network
        </button>
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
      
      // Build coordinate array: start node + waypoints (if any) + end node.
      // This supports both straight edges (no waypoints) and curved edges (with waypoints).
      const coordinates: Array<[number, number]> = [
        [toLon(a.x), toLat(a.y)],
      ];
      
      if (e.waypoints && e.waypoints.length > 0) {
        for (const wp of e.waypoints) {
          coordinates.push([toLon(wp.x), toLat(wp.y)]);
        }
      }
      
      coordinates.push([toLon(b.x), toLat(b.y)]);
      
      return {
        type: 'Feature' as const,
        properties: { id: e.id, trackId: e.trackId ?? '' },
        geometry: {
          type: 'LineString' as const,
          coordinates,
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
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#94a3b8',
      'line-width': 2,
    },
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

// ── Train layers (clustered) ───────────────────────────────────────────

function addTrainLayers(map: maplibregl.Map) {
  map.addSource('trains', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
    cluster: true,
    clusterMaxZoom: 13,
    clusterRadius: 45,
  });

  // Cluster circles (zoomed out).
  map.addLayer({
    id: 'train-cluster',
    type: 'circle',
    source: 'trains',
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': [
        'step',
        ['get', 'point_count'],
        '#fca5a5',
        10, '#f87171',
        25, '#ef4444',
      ],
      'circle-radius': [
        'step',
        ['get', 'point_count'],
        14,
        10, 18,
        25, 24,
      ],
      'circle-stroke-color': '#fff',
      'circle-stroke-width': 2,
    },
  });

  // Cluster count labels.
  map.addLayer({
    id: 'train-cluster-count',
    type: 'symbol',
    source: 'trains',
    filter: ['has', 'point_count'],
    layout: {
      'text-field': ['get', 'point_count_abbreviated'],
      'text-size': 12,
      'text-font': ['Open Sans Bold'],
    },
    paint: {
      'text-color': '#fff',
    },
  });

  // Individual train points (zoomed in, no cluster).
  map.addLayer({
    id: 'train-point',
    type: 'circle',
    source: 'trains',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-color': '#dc2626',
      'circle-radius': 6,
      'circle-stroke-color': '#fff',
      'circle-stroke-width': 2,
    },
  });
}

// ── Block layers ───────────────────────────────────────────────────────

function addBlockLayers(map: maplibregl.Map) {
  map.addSource('blocks', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  });

  map.addLayer({
    id: 'block-segments',
    type: 'line',
    source: 'blocks',
    layout: {
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#f59e0b',
      'line-width': 6,
      'line-opacity': 0.5,
    },
  });
}

// ── Restriction layers ─────────────────────────────────────────────────

/**
 * Add a restriction overlay layer. Restrictions are rendered as red
 * dashed lines over the affected track segment. Data is supplied by the
 * backend (Phase 10a.8) and pushed via the `restrictions` source.
 */
function addRestrictionLayers(map: maplibregl.Map) {
  map.addSource('restrictions', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  });

  map.addLayer({
    id: 'restriction-segments',
    type: 'line',
    source: 'restrictions',
    layout: {
      'line-cap': 'butt',
    },
    paint: {
      'line-color': '#dc2626',
      'line-width': 4,
      'line-dasharray': [2, 1],
      'line-opacity': 0.8,
    },
  });
}

// ── Map interactions (clicks, popups) ─────────────────────────────────

/**
 * Wire up click handlers:
 * - Cluster click → zoom into the cluster.
 * - Train point click → show a popup with train details + select in store.
 */
function wireMapInteractions(map: maplibregl.Map) {
  let popup: maplibregl.Popup | null = null;

  // Cluster click → zoom in.
  map.on('click', 'train-cluster', (e) => {
    const features = map.queryRenderedFeatures(e.point, { layers: ['train-cluster'] });
    const clusterId = features[0]?.properties?.cluster_id;
    if (clusterId == null) return;
    const source = map.getSource('trains') as maplibregl.GeoJSONSource | undefined;
    source?.getClusterExpansionZoom(clusterId).then((zoom) => {
      if (zoom == null) return;
      map.easeTo({
        center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
        zoom: zoom + 0.5,
      });
    });
  });

  // Cursor pointer on hoverable layers.
  for (const layer of ['train-cluster', 'train-point']) {
    map.on('mouseenter', layer, () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', layer, () => {
      map.getCanvas().style.cursor = '';
    });
  }

  // Train point click → popup + selection.
  map.on('click', 'train-point', (e) => {
    const f = e.features?.[0];
    if (!f) return;
    const props = f.properties as {
      trainId: string;
      trackId: string;
      speed: number;
    };
    const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];

    useMapStore.getState().selectTrain(props.trainId);

    popup?.remove();
    popup = new maplibregl.Popup({ offset: 10, closeButton: true })
      .setLngLat(coords)
      .setHTML(
        `<div style="font-family:system-ui;font-size:12px;line-height:1.5">
           <strong style="font-size:13px">${props.trainId}</strong><br/>
           Track: ${props.trackId || '—'}<br/>
           Speed: ${props.speed ?? 0} km/h
         </div>`,
      )
      .addTo(map);
  });
}
