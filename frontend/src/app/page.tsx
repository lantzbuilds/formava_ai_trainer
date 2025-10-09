'use client';

import React, { useState, useEffect } from 'react';
import Navigation from '@/components/Navigation';
import LandingPage from '@/components/pages/LandingPage';
import { Page } from '@/types';
import { useAuth } from '@/contexts/AuthContext';

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<Page>('landing');
  const { user, isLoading } = useAuth();

  // Set initial page based on auth state
  useEffect(() => {
    if (!isLoading) {
      if (user) {
        setCurrentPage('dashboard');
      } else {
        setCurrentPage('landing');
      }
    }
  }, [user, isLoading]);

  const handlePageChange = (page: Page) => {
    setCurrentPage(page);
  };

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'landing':
        return <LandingPage onPageChange={handlePageChange} />;
      case 'login':
        return <div className="p-8">Login Page - Coming Soon</div>;
      case 'register':
        return <div className="p-8">Register Page - Coming Soon</div>;
      case 'dashboard':
        return <div className="p-8">Dashboard Page - Coming Soon</div>;
      case 'ai_recs':
        return <div className="p-8">AI Recommendations Page - Coming Soon</div>;
      case 'profile':
        return <div className="p-8">Profile Page - Coming Soon</div>;
      default:
        return <LandingPage onPageChange={handlePageChange} />;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation currentPage={currentPage} onPageChange={handlePageChange} />
      <main>
        {renderCurrentPage()}
      </main>
    </div>
  );
}