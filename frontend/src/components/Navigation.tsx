'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Page } from '@/types';

interface NavigationProps {
  currentPage: Page;
  onPageChange: (page: Page) => void;
}

export default function Navigation({ currentPage, onPageChange }: NavigationProps) {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    onPageChange('landing');
  };

  const navItems = [
    { id: 'landing' as Page, label: 'Home', show: true },
    { id: 'login' as Page, label: 'Login', show: !user },
    { id: 'register' as Page, label: 'Register', show: !user },
    { id: 'dashboard' as Page, label: 'Dashboard', show: !!user },
    { id: 'ai_recs' as Page, label: 'AI Recs', show: !!user },
    { id: 'profile' as Page, label: 'Profile', show: !!user },
  ];

  return (
    <nav className="bg-gray-50 border-b border-gray-200 px-4 py-3">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <img 
              src="/formava_icon_v0_1.svg" 
              alt="Formava" 
              className="h-8 w-8"
            />
            <span className="text-xl font-bold text-gray-900">Formava AI Fitness</span>
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            {navItems.map((item) => {
              if (!item.show) return null;
              
              const isActive = currentPage === item.id;
              
              return (
                <button
                  key={item.id}
                  onClick={() => onPageChange(item.id)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
            
            {user && (
              <button
                onClick={handleLogout}
                className="px-4 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

