'use client';

import React, { createContext, useContext, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  currentTheme: Theme;
  changeTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<Theme>('light');

  const changeTheme = (theme: Theme) => {
    setCurrentTheme(theme);
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme);
  };

  return (
    <ThemeContext.Provider value={{ currentTheme, changeTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

interface ThemeManagerProps {
  currentTheme: Theme;
  onThemeChange: (theme: Theme) => void;
  isExpanded: boolean;
  onToggle: () => void;
}

export function ThemeManager({ 
  currentTheme, 
  onThemeChange, 
  isExpanded, 
  onToggle 
}: ThemeManagerProps) {
  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-muted-foreground">Theme</p>
        <button
          onClick={onToggle}
          className="text-xs px-2 py-1 rounded hover:bg-muted"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>
      
      {isExpanded && (
        <div className="space-y-1">
          <button
            onClick={() => onThemeChange('light')}
            className={`text-xs px-2 py-1 rounded text-left w-full ${
              currentTheme === 'light' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
            }`}
          >
            Light
          </button>
          <button
            onClick={() => onThemeChange('dark')}
            className={`text-xs px-2 py-1 rounded text-left w-full ${
              currentTheme === 'dark' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
            }`}
          >
            Dark
          </button>
        </div>
      )}
    </div>
  );
}
