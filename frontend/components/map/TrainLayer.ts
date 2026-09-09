/**
 * TrainLayer – data transformation utilities for train position rendering.
 *
 * Phase 10a.3: Provides GeoJSON builders.
 * Phase 10a.6: Will be wired into Maplibre GL layers (clustering, popups).
 */

import { toLon, toLat } from './MapContainer';

// ── Types ──────────────────────────────────────────────────────────────

export interface TrainPosition {
  trainId: string;
  x: number;
  y: number;
  trackId?: string;
  speed?: number;
  fromTime: string; // ISO 8601
  toTime: string;   // ISO 8601
}

// ── GeoJSON builders ───────────────────────────────────────────────────

/**
 * Convert an array of TrainPosition into a GeoJSON FeatureCollection.
 * Each feature carries the train metadata in `properties`.
 */
export function trainPositionsToGeoJSON(positions: TrainPosition[]) {
  return {
    type: 'FeatureCollection' as const,
    features: positions.map((p) => ({
      type: 'Feature' as const,
      properties: {
        trainId: p.trainId,
        trackId: p.trackId ?? '',
        speed: p.speed ?? 0,
        fromTime: p.fromTime,
        toTime: p.toTime,
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [toLon(p.x), toLat(p.y)],
      },
    })),
  };
}

/**
 * Filter positions that are valid at the given time.
 * A position is valid when `fromTime <= t <= toTime`.
 */
export function filterByTime(positions: TrainPosition[], t: Date): TrainPosition[] {
  const ms = t.getTime();
  return positions.filter(
    (p) => new Date(p.fromTime).getTime() <= ms && ms <= new Date(p.toTime).getTime(),
  );
}

// ── Mock data (replaced by useTrainPositions in 10a.4) ────────────────

export const MOCK_TRAIN_POSITIONS: TrainPosition[] = [
  {
    trainId: 'TRN-001',
    x: 5_000,
    y: 0,
    trackId: 'T1',
    speed: 80,
    fromTime: '2026-09-09T08:00:00Z',
    toTime: '2026-09-09T12:00:00Z',
  },
  {
    trainId: 'TRN-002',
    x: 15_000,
    y: 0,
    trackId: 'T1',
    speed: 60,
    fromTime: '2026-09-09T08:00:00Z',
    toTime: '2026-09-09T12:00:00Z',
  },
  {
    trainId: 'TRN-003',
    x: 25_000,
    y: 2_500,
    trackId: 'T3',
    speed: 100,
    fromTime: '2026-09-09T08:00:00Z',
    toTime: '2026-09-09T12:00:00Z',
  },
  {
    trainId: 'TRN-004',
    x: 35_000,
    y: 5_000,
    trackId: 'T4',
    speed: 70,
    fromTime: '2026-09-09T08:00:00Z',
    toTime: '2026-09-09T12:00:00Z',
  },
];
