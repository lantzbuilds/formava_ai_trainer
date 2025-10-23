/**
 * React Query hooks for dashboard data
 */

import { useQuery } from '@tanstack/react-query';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DashboardData {
  welcome_message: string;
  total_workouts: number;
  recent_workouts: number;
  avg_workouts_per_week: number;
  last_workout_date: string | null;
  current_streak: number;
  fitness_goals: string[];
  active_injuries: Array<{
    description: string;
    body_part: string;
    severity: string;
    date_injured: string;
    notes?: string;
  }>;
}

export function useDashboard(userId: string | null | undefined) {
  return useQuery({
    queryKey: ['dashboard', userId],
    queryFn: async () => {
      if (!userId) throw new Error('User ID is required');
      
      const token = localStorage.getItem('auth_token');
      if (!token) throw new Error('Not authenticated');

      const response = await fetch(`${API_BASE_URL}/api/users/${userId}/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch dashboard data');
      }

      return response.json() as Promise<DashboardData>;
    },
    enabled: !!userId, // Only run query if userId exists
    staleTime: 2 * 60 * 1000, // Consider data fresh for 2 minutes
    refetchOnWindowFocus: true, // Refetch when user returns to tab
  });
}

