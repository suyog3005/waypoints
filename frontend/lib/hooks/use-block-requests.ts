'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api/client';
import { toast } from 'sonner';
import type { BlockRequestCreate, BlockRequestResponse, BlockRequestUpdate } from './types';

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
