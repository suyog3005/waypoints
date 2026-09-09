'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { TrainOut } from './types';

interface TrainsFilters {
  active_only?: boolean;
}

export function useTrains(filters?: TrainsFilters) {
  const queryParams = new URLSearchParams();
  if (filters?.active_only) queryParams.append('active_only', String(filters.active_only));

  const path = `/trains${queryParams.toString() ? `?${queryParams}` : ''}`;

  return useQuery({
    queryKey: ['trains', filters],
    queryFn: async () => {
      const { data } = await apiFetch<TrainOut[]>(path);
      return data || [];
    },
    staleTime: 10 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
