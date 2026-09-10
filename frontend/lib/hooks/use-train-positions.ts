'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { DataTile } from '@/stores/tile.store';
import type { TrainPosition } from '@/components/map/TrainLayer';

// ── Response types ─────────────────────────────────────────────────────

export interface TrainPositionsResponse {
  /**
   * Positions grouped by tile ID — the unit of delta transfer. Only tiles whose
   * version changed are present, each with its FULL position list. The consumer
   * (usePollingCoordinator) merges these into a per-tile cache so unchanged
   * tiles keep their positions across polls.
   */
  tiles: Record<string, TrainPosition[]>;
  meta: {
    dataTileVersions: Record<string, string>; // tileId -> new UUID version
    businessClock: string; // ISO 8601
  };
}

// ── Hook ───────────────────────────────────────────────────────────────

interface UseTrainPositionsParams {
  /** Visible tiles (with optional cached versions for delta transfer). */
  tiles: DataTile[];
  /** Whether to enable polling (disable when tab is hidden). */
  enabled?: boolean;
}

/**
 * useTrainPositions – poll train positions for visible tiles.
 *
 * Phase 10a.4: POST /trainpositions with tile versioning.
 * - Sends visible tiles + cached versions (delta transfer).
 * - Refetches every 2 seconds.
 * - Updates tile version cache from response meta.
 *
 * TODO (10a.5): Wire tile version cache updates into tile.store.
 */
export function useTrainPositions({ tiles, enabled = true }: UseTrainPositionsParams) {
  return useQuery({
    queryKey: ['trainpositions', tiles.map((t) => t.id).sort()],
    queryFn: async () => {
      const { data } = await apiFetch<TrainPositionsResponse>('/trainpositions', {
        method: 'POST',
        body: JSON.stringify({ tiles }),
      });
      return data;
    },
    enabled: enabled && tiles.length > 0,
    staleTime: 0, // always fresh
    refetchInterval: 2_000, // 2 seconds
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
