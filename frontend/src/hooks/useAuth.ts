/**
 * React Query hooks for authentication
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData extends LoginCredentials {
  email: string;
  age?: number;
  sex?: string;
  height_cm?: number;
  weight_kg?: number;
  experience_level?: string;
  preferred_units?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
  };
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const response = await apiClient.login(credentials.username, credentials.password);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Login failed');
      }
      return response.data as AuthResponse;
    },
    onSuccess: (data) => {
      // Store token
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_data', JSON.stringify(data.user));
      
      // Invalidate and refetch user-related queries
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userData: RegisterData) => {
      const response = await apiClient.register(userData);
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Registration failed');
      }
      return response.data as AuthResponse;
    },
    onSuccess: (data) => {
      // Store token
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_data', JSON.stringify(data.user));
      
      // Invalidate and refetch user-related queries
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
}

export function useDemoLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await fetch('http://localhost:8000/api/auth/demo-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Demo login failed');
      }
      
      return response.json() as Promise<AuthResponse>;
    },
    onSuccess: (data) => {
      // Store token
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_data', JSON.stringify(data.user));
      
      // Invalidate and refetch user-related queries
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiClient.logout();
    },
    onSuccess: () => {
      // Clear tokens
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      
      // Clear all cached queries
      queryClient.clear();
    },
  });
}

