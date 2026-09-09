/**
 * Train Positioning – time-based filtering and block derivation.
 *
 * Phase 10a.4: Utility functions for filtering train positions by time
 * and deriving block occupancy from positions.
 *
 * Note: Some of these overlap with TrainLayer.ts / BlockLayer.ts helpers.
 * This module provides the canonical implementations that the polling
 * coordinator (10a.5) and map layers (10a.6) will use.
 */

import type { TrainPosition } from '@/components/map/TrainLayer';
import type { BlockSegment } from '@/components/map/BlockLayer';

// ── Time filtering ─────────────────────────────────────────────────────

/**
 * Filter positions that are valid at the given time.
 * A position is valid when `fromTime <= t <= toTime`.
 *
 * @param positions - All known train positions
 * @param targetTime - The time to filter for
 * @returns Positions valid at targetTime
 */
export function filterPositionsByTime(
  positions: TrainPosition[],
  targetTime: Date,
): TrainPosition[] {
  const ms = targetTime.getTime();
  return positions.filter(
    (p) => new Date(p.fromTime).getTime() <= ms && ms <= new Date(p.toTime).getTime(),
  );
}

// ── Block derivation ───────────────────────────────────────────────────

/** Half-length of a block segment in meters (1 000 m on each side). */
const BLOCK_HALF_LENGTH = 1_000;

/**
 * Derive block occupancy segments from train positions.
 *
 * MVP heuristic: each train occupies a 2 000 m segment centred on its
 * position. Direction is inferred from trackId (simplified).
 *
 * In production, this will come from the backend's block occupancy data.
 *
 * @param positions - Train positions (already time-filtered)
 * @returns Block segments
 */
export function deriveBlocksFromPositions(positions: TrainPosition[]): BlockSegment[] {
  return positions.map((p) => {
    // Simplified direction inference by trackId.
    // A real implementation would use base graph edge geometry.
    const dx = p.trackId === 'T3' ? 0.7 : 1;
    const dy = p.trackId === 'T3' ? 0.7 : 0;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ux = dx / len;
    const uy = dy / len;

    return {
      id: `blk-${p.trainId}`,
      trackId: p.trackId ?? 'unknown',
      trainId: p.trainId,
      x1: p.x - ux * BLOCK_HALF_LENGTH,
      y1: p.y - uy * BLOCK_HALF_LENGTH,
      x2: p.x + ux * BLOCK_HALF_LENGTH,
      y2: p.y + uy * BLOCK_HALF_LENGTH,
      occupied: true,
    };
  });
}

// ── Position interpolation (for smooth animation) ─────────────────────

/**
 * Interpolate a train's position between two known positions.
 *
 * @param from - Earlier position
 * @param to - Later position
 * @param t - Interpolation factor (0 = from, 1 = to)
 * @returns Interpolated {x, y}
 */
export function interpolatePosition(
  from: { x: number; y: number },
  to: { x: number; y: number },
  t: number,
): { x: number; y: number } {
  const clamped = Math.max(0, Math.min(1, t));
  return {
    x: from.x + (to.x - from.x) * clamped,
    y: from.y + (to.y - from.y) * clamped,
  };
}
