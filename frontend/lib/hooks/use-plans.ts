'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import type { PlanSummaryOut } from './types';

interface PlansFilters {
  status?: string;
  section_id?: string;
}

export function usePlans(filters?: PlansFilters) {
  const queryParams = new URLSearchParams();
  if (filters?.status) queryParams.append('status', filters.status);
  if (filters?.section_id) queryParams.append('section_id', filters.section_id);

  const path = `/plans${queryParams.toString() ? `?${queryParams}` : ''}`;

  return useQuery({
    queryKey: ['plans', filters],
    queryFn: async () => {
      const { data } = await apiFetch<PlanSummaryOut[]>(path);
      return data || [];
    },
    staleTime: 10 * 1000, // 10 seconds
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
