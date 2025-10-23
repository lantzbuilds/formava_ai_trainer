/**
 * React Query hooks for AI recommendations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AIRecsSummary {
  profile_summary: {
    experience_level: string;
    fitness_goals: string[];
    workout_days: number;
    workout_duration: number;
    active_injuries: Array<{
      description: string;
      body_part: string;
    }>;
  };
  workout_summary: {
    workouts_last_30_days: number;
    avg_exercises_per_workout: number;
  };
  exercises_summary: {
    total_exercises_available: number;
  };
}

export interface GenerateRoutineRequest {
  split_type?: string;
  period?: string;
  include_cardio?: boolean;
  title?: string;
}

export function useAIRecsSummary(userId: string | null | undefined) {
  return useQuery({
    queryKey: ['aiRecsSummary', userId],
    queryFn: async () => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(
        `${API_BASE_URL}/api/users/${userId}/ai-recommendations/summary`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch AI recs summary');
      }

      return response.json() as Promise<AIRecsSummary>;
    },
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
  });
}

export function useGenerateRoutine(userId: string | null | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: GenerateRoutineRequest) => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(
        `${API_BASE_URL}/api/users/${userId}/generate-routine`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            split_type: request.split_type || 'auto',
            period: request.period || 'week',
            include_cardio: request.include_cardio ?? true,
            title: request.title,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate routine');
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate AI recs summary to reflect updated data
      queryClient.invalidateQueries({ queryKey: ['aiRecsSummary', userId] });
    },
  });
}

export function useSaveToHevy(userId: string | null | undefined) {
  return useMutation({
    mutationFn: async (routineFolder: any) => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(
        `${API_BASE_URL}/api/users/${userId}/save-to-hevy`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(routineFolder),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save to Hevy');
      }

      return response.json();
    },
  });
}

