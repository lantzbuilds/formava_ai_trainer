/**
 * React Query hooks for Hevy sync
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SyncStatusData {
  status: string;
  message: string;
}

export function useSyncStatus(userId: string | null | undefined) {
  return useQuery({
    queryKey: ['syncStatus', userId],
    queryFn: async () => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(
        `${API_BASE_URL}/api/users/${userId}/sync-status`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch sync status');
      }

      return response.json() as Promise<SyncStatusData>;
    },
    enabled: !!userId,
    refetchInterval: (query) => {
      // Poll every 2 seconds while syncing, otherwise don't poll
      const status = query.state.data?.status;
      return status === 'syncing' ? 2000 : false;
    },
  });
}

export function useSyncHevy(userId: string | null | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (syncType: 'recent' | 'full' = 'recent') => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(
        `${API_BASE_URL}/api/users/${userId}/sync-hevy`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ sync_type: syncType }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start sync');
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate sync status to start polling
      queryClient.invalidateQueries({ queryKey: ['syncStatus', userId] });
      // Invalidate dashboard data as it will be updated after sync
      queryClient.invalidateQueries({ queryKey: ['dashboard', userId] });
    },
  });
}

