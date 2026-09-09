/**
 * BlockLayer – derives block occupancy segments from train positions.
 *
 * Phase 10a.3: Provides GeoJSON builders.
 * Phase 10a.6: Will be wired into Maplibre GL line layers.
 */

import { toLon, toLat } from './MapContainer';
import type { TrainPosition } from './TrainLayer';

// ── Types ──────────────────────────────────────────────────────────────

export interface BlockSegment {
  id: string;
  trackId: string;
  trainId: string;
  /** Start point (meters). */
  x1: number;
  y1: number;
  /** End point (meters). */
  x2: number;
  y2: number;
  /** Occupied by a train. */
  occupied: boolean;
}

// ── Derivation ─────────────────────────────────────────────────────────

/**
 * Derive block segments from train positions.
 *
 * MVP heuristic: each train occupies a 2 000 m segment centred on its
 * position, along the track direction. In production this will come from
 * the backend's block occupancy data.
 */
export function deriveBlocks(positions: TrainPosition[]): BlockSegment[] {
  const SEGMENT_HALF = 1_000; // 1 000 m on each side

  return positions.map((p) => {
    // Determine direction from trackId (simplified: horizontal for T1/T2,
    // diagonal for T3, horizontal for T4). A real implementation would
    // use the base graph edge geometry.
    const dx = p.trackId === 'T3' ? 0.7 : 1;
    const dy = p.trackId === 'T3' ? 0.7 : 0;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ux = dx / len;
    const uy = dy / len;

    return {
      id: `blk-${p.trainId}`,
      trackId: p.trackId ?? 'unknown',
      trainId: p.trainId,
      x1: p.x - ux * SEGMENT_HALF,
      y1: p.y - uy * SEGMENT_HALF,
      x2: p.x + ux * SEGMENT_HALF,
      y2: p.y + uy * SEGMENT_HALF,
      occupied: true,
    };
  });
}

// ── GeoJSON builder ────────────────────────────────────────────────────

export function blocksToGeoJSON(blocks: BlockSegment[]) {
  return {
    type: 'FeatureCollection' as const,
    features: blocks.map((b) => ({
      type: 'Feature' as const,
      properties: {
        id: b.id,
        trackId: b.trackId,
        trainId: b.trainId,
        occupied: b.occupied,
      },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [toLon(b.x1), toLat(b.y1)],
          [toLon(b.x2), toLat(b.y2)],
        ],
      },
    })),
  };
}
