'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, LoginForm, RegisterForm } from '@/types';
import { apiClient } from '@/lib/api/client';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginForm) => Promise<boolean>;
  register: (userData: RegisterForm) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if user is logged in (you'll need to implement this endpoint)
        const token = localStorage.getItem('auth_token');
        if (token) {
          // For now, we'll store user data in localStorage
          // In a real app, you'd validate the token with the backend
          const userData = localStorage.getItem('user_data');
          if (userData) {
            setUser(JSON.parse(userData));
          }
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials: LoginForm): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.login(credentials.username, credentials.password);
      
      if (response.success && response.data) {
        const userData = response.data.user;
        setUser(userData);
        
        // Store auth data (in a real app, you'd store a JWT token)
        localStorage.setItem('auth_token', 'dummy_token'); // Replace with actual token
        localStorage.setItem('user_data', JSON.stringify(userData));
        
        return true;
      } else {
        setError(response.error || 'Login failed');
        return false;
      }
    } catch (err) {
      setError('An unexpected error occurred during login');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterForm): Promise<boolean> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.register(userData);
      
      if (response.success && response.data) {
        // Auto-login after successful registration
        return await login({
          username: userData.username,
          password: userData.password,
        });
      } else {
        setError(response.error || 'Registration failed');
        return false;
      }
    } catch (err) {
      setError('An unexpected error occurred during registration');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    
    try {
      await apiClient.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value: AuthContextType = {
    user,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

