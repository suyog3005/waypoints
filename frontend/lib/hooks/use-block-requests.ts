'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import { toast } from 'sonner';
import type {
  BlockRequestCreate,
  BlockRequestResponse,
  BlockRequestUpdate,
  DepartmentOut,
  ExecutionStateOut,
  UserOut,
} from './types';

export function useBlockRequests(status?: string | null) {
  const path = status ? `/block-requests?status=${status}` : '/block-requests';
  return useQuery({
    queryKey: ['block-requests', status ?? 'all'],
    queryFn: async () => {
      const { data } = await apiFetch<BlockRequestResponse[]>(path);
      return data || [];
    },
    staleTime: 5 * 1000,
    retry: 1,
    refetchOnWindowFocus: true,
  });
}

export function useBlockRequest(id: string | undefined) {
  return useQuery({
    queryKey: ['block-request', id],
    queryFn: async () => {
      const { data } = await apiFetch<BlockRequestResponse>(`/block-requests/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 1000,
    retry: 1,
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: ['departments'],
    queryFn: async () => {
      const { data } = await apiFetch<DepartmentOut[]>('/departments');
      return data || [];
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data } = await apiFetch<UserOut[]>('/users');
      return data || [];
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

export function useUpdateExecutionState(requestId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<ExecutionStateOut>) => {
      const { data: response } = await apiFetch<BlockRequestResponse>(
        `/block-requests/${requestId}/execution`,
        {
          method: 'PATCH',
          body: JSON.stringify(data),
          headers: { 'Content-Type': 'application/json' },
        },
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['block-requests'] });
      queryClient.invalidateQueries({ queryKey: ['block-request', requestId] });
      toast.success('Execution state updated');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to update execution state';
      toast.error(message);
    },
  });
}

export function useCreateBlockRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BlockRequestCreate) => {
      const { data: response } = await apiFetch<BlockRequestResponse>('/block-requests', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' },
      });
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['block-requests'] });
      toast.success('Block request submitted successfully');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to submit block request';
      toast.error(message);
    },
  });
}

export function useUpdateBlockRequest(requestId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BlockRequestUpdate) => {
      const { data: response } = await apiFetch<BlockRequestResponse>(
        `/block-requests/${requestId}`,
        {
          method: 'PATCH',
          body: JSON.stringify(data),
          headers: { 'Content-Type': 'application/json' },
        }
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['block-requests'] });
      queryClient.invalidateQueries({ queryKey: ['block-request', requestId] });
      toast.success('Block request updated successfully');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : 'Failed to update block request';
      toast.error(message);
    },
  });
}
