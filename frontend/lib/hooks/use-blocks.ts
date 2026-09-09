'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { BlockOut } from './types';

interface BlocksFilters {
  plan_id?: string;
  track_id?: string;
}

export function useBlocks(filters?: BlocksFilters) {
  const queryParams = new URLSearchParams();
  if (filters?.plan_id) queryParams.append('plan_id', filters.plan_id);
  if (filters?.track_id) queryParams.append('track_id', filters.track_id);

  const path = `/blocks${queryParams.toString() ? `?${queryParams}` : ''}`;

  return useQuery({
    queryKey: ['blocks', filters],
    queryFn: async () => {
      const { data } = await apiFetch<BlockOut[]>(path);
      return data || [];
    },
    staleTime: 10 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
