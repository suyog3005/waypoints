/**
 * Tile Management – 3D tiling strategy (X, Y, Time).
 *
 * Phase 10a.4: Compute tile boundaries, visible tiles, and time quantization.
 *
 * Tile ID format: "{x}_{y}_{yyyy-MM-ddTHH:mm}"
 *   - x, y: tile grid coordinates (integer)
 *   - time: 15-minute bucket (quantized)
 *
 * Example: "125000_-10000_2026-08-31T09:15"
 */

import { format } from 'date-fns';

// ── Constants ──────────────────────────────────────────────────────────

/** Default tile size in meters (10 km × 10 km). */
export const DEFAULT_TILE_SIZE = 10_000;

/** Time bucket interval in minutes (15 min). */
export const TIME_BUCKET_MINUTES = 15;

// ── Types ──────────────────────────────────────────────────────────────

export interface TileBoundary {
  /** Tile grid X coordinate. */
  tileX: number;
  /** Tile grid Y coordinate. */
  tileY: number;
  /** World-space bounds (meters). */
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface ViewportExtent {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

// ── Core functions ─────────────────────────────────────────────────────

/**
 * Quantize a timestamp to a 15-minute bucket.
 * Returns an ISO string formatted as "yyyy-MM-ddTHH:mm".
 *
 * Example: 2026-08-31T09:23:45 → "2026-08-31T09:15"
 */
export function roundToInterval(timestamp: Date, intervalMin = TIME_BUCKET_MINUTES): string {
  const ms = timestamp.getTime();
  const intervalMs = intervalMin * 60_000;
  const bucketed = Math.floor(ms / intervalMs) * intervalMs;
  return format(new Date(bucketed), 'yyyy-MM-ddTHH:mm');
}

/**
 * Compute the tile grid coordinate for a world-space position.
 *
 * @param x - World X in meters
 * @param y - World Y in meters
 * @param tileSize - Tile size in meters (default 10 000)
 * @returns [tileX, tileY] integer grid coordinates
 */
export function positionToTile(x: number, y: number, tileSize = DEFAULT_TILE_SIZE): [number, number] {
  return [Math.floor(x / tileSize), Math.floor(y / tileSize)];
}

/**
 * Compute which tiles overlap a given viewport extent.
 *
 * @param extent - Viewport bounds in meters
 * @param tileSize - Tile size in meters
 * @param timestamp - Current display time (for tile ID)
 * @returns Array of tile IDs (e.g., "125000_-10000_2026-08-31T09:15")
 */
export function getVisibleTiles(
  extent: ViewportExtent,
  timestamp: Date,
  tileSize = DEFAULT_TILE_SIZE,
): string[] {
  const [minTileX, minTileY] = positionToTile(extent.minX, extent.minY, tileSize);
  const [maxTileX, maxTileY] = positionToTile(extent.maxX, extent.maxY, tileSize);
  const timeBucket = roundToInterval(timestamp);

  const tiles: string[] = [];
  for (let tx = minTileX; tx <= maxTileX; tx++) {
    for (let ty = minTileY; ty <= maxTileY; ty++) {
      tiles.push(`${tx}_${ty}_${timeBucket}`);
    }
  }
  return tiles;
}

/**
 * Compute the global tile grid from all node positions.
 * Returns the bounding box of all tiles that contain at least one node.
 *
 * @param nodes - Array of {x, y} positions in meters
 * @param tileSize - Tile size in meters
 * @returns Tile boundaries covering all nodes
 */
export function calculateTileBoundaries(
  nodes: { x: number; y: number }[],
  tileSize = DEFAULT_TILE_SIZE,
): TileBoundary[] {
  if (nodes.length === 0) return [];

  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;

  for (const n of nodes) {
    minX = Math.min(minX, n.x);
    maxX = Math.max(maxX, n.x);
    minY = Math.min(minY, n.y);
    maxY = Math.max(maxY, n.y);
  }

  const [minTileX, minTileY] = positionToTile(minX, minY, tileSize);
  const [maxTileX, maxTileY] = positionToTile(maxX, maxY, tileSize);

  const boundaries: TileBoundary[] = [];
  for (let tx = minTileX; tx <= maxTileX; tx++) {
    for (let ty = minTileY; ty <= maxTileY; ty++) {
      boundaries.push({
        tileX: tx,
        tileY: ty,
        minX: tx * tileSize,
        maxX: (tx + 1) * tileSize,
        minY: ty * tileSize,
        maxY: (ty + 1) * tileSize,
      });
    }
  }
  return boundaries;
}

/**
 * Parse a tile ID string into its components.
 *
 * @param tileId - e.g., "125000_-10000_2026-08-31T09:15"
 * @returns { tileX, tileY, time } or null if malformed
 */
export function parseTileId(tileId: string): { tileX: number; tileY: number; time: string } | null {
  // Format: "{x}_{y}_{yyyy-MM-ddTHH:mm}"
  // The time part contains a 'T' and ':' so we split from the right.
  const lastUnderscore = tileId.lastIndexOf('_');
  if (lastUnderscore === -1) return null;

  const time = tileId.slice(lastUnderscore + 1);
  const xyPart = tileId.slice(0, lastUnderscore);

  const underscoreIdx = xyPart.indexOf('_');
  if (underscoreIdx === -1) return null;

  const tileX = parseInt(xyPart.slice(0, underscoreIdx), 10);
  const tileY = parseInt(xyPart.slice(underscoreIdx + 1), 10);

  if (isNaN(tileX) || isNaN(tileY)) return null;

  return { tileX, tileY, time };
}
