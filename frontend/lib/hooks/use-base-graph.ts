'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { BaseGraphData } from '@/components/map/MapContainer';

/**
 * useBaseGraph – fetch the infrastructure graph (nodes + edges).
 *
 * Phase 10a.4: GET /basegraph with a long staleTime (1 hour).
 * The base graph rarely changes, so we cache aggressively.
 *
 * TODO (10a.4): Add Dexie/IndexedDB persistence for offline support.
 */
export function useBaseGraph() {
  return useQuery({
    queryKey: ['basegraph'],
    queryFn: async () => {
      const { data } = await apiFetch<BaseGraphData>('/basegraph');
      return data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 6 * 60 * 60 * 1000, // 6 hours
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
