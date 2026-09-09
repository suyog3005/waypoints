'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { TrackOut } from './types';

interface TracksFilters {
  section_id?: string;
  active_only?: boolean;
}

export function useTracks(filters?: TracksFilters) {
  const queryParams = new URLSearchParams();
  if (filters?.section_id) queryParams.append('section_id', filters.section_id);
  if (filters?.active_only) queryParams.append('active_only', String(filters.active_only));

  const path = `/tracks${queryParams.toString() ? `?${queryParams}` : ''}`;

  return useQuery({
    queryKey: ['tracks', filters],
    queryFn: async () => {
      const { data } = await apiFetch<TrackOut[]>(path);
      return data || [];
    },
    staleTime: 10 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
