'use client';

import React, { useState, useEffect } from 'react';
import { Layout } from '@/components/layout/Layout';
import { LandingPage } from '@/components/pages/LandingPage';
import { LoginPageEnhanced as LoginPage } from '@/components/pages/LoginPageEnhanced';
import { RegistrationPage } from '@/components/pages/RegistrationPage';
import { DashboardPageEnhanced as DashboardPage } from '@/components/pages/DashboardPageEnhanced';
import { AIRecommendationsPage } from '@/components/pages/AIRecommendationsPage';
import { ProfilePage } from '@/components/pages/ProfilePage';
import { ThemeManager, useTheme } from '@/components/ThemeManager';
import { useAuth } from '@/contexts/AuthContext';

type PageType = 'landing' | 'login' | 'register' | 'dashboard' | 'ai-recommendations' | 'profile';

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageType>('landing');
  const { currentTheme, changeTheme } = useTheme();
  const [isThemeManagerExpanded, setIsThemeManagerExpanded] = useState(false);
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

  const handlePageChange = (page: PageType) => {
    setCurrentPage(page);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'landing':
        return <LandingPage onPageChange={handlePageChange} />;
      case 'login':
        return <LoginPage onPageChange={handlePageChange} />;
      case 'register':
        return <RegistrationPage onPageChange={handlePageChange} />;
      case 'dashboard':
        return <DashboardPage />;
      case 'ai-recommendations':
        return <AIRecommendationsPage />;
      case 'profile':
        return <ProfilePage />;
      default:
        return <LandingPage onPageChange={handlePageChange} />;
    }
  };

  const showNavigation = !['landing', 'login', 'register'].includes(currentPage);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Demo Controls - Only show in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed top-4 right-4 z-50 flex flex-col gap-3">
          {/* Theme Manager */}
          <div className="relative">
            <ThemeManager 
              currentTheme={currentTheme} 
              onThemeChange={changeTheme}
              isExpanded={isThemeManagerExpanded}
              onToggle={() => setIsThemeManagerExpanded(!isThemeManagerExpanded)}
            />
          </div>

          {/* Demo Navigation Controls */}
          <div className="bg-card border border-border rounded-lg shadow-lg p-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Demo Navigation</p>
            <div className="flex flex-col gap-1">
              <button
                onClick={() => setCurrentPage('landing')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'landing' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                Landing
              </button>
              <button
                onClick={() => setCurrentPage('login')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'login' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                Login
              </button>
              <button
                onClick={() => setCurrentPage('register')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'register' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                Register
              </button>
              <button
                onClick={() => setCurrentPage('dashboard')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'dashboard' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setCurrentPage('ai-recommendations')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'ai-recommendations' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                AI Trainer
              </button>
              <button
                onClick={() => setCurrentPage('profile')}
                className={`text-xs px-2 py-1 rounded text-left ${currentPage === 'profile' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
              >
                Profile
              </button>
            </div>
          </div>
        </div>
      )}

      <Layout showNavigation={showNavigation}>
        {renderPage()}
      </Layout>
    </div>
  );
}