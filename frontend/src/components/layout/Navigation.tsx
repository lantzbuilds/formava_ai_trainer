import { useState } from 'react';
import { Button } from '../ui/button';
import { Menu, X, Dumbbell, User, BarChart3, Brain, Home, LogIn } from 'lucide-react';

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState('landing');

  const navItems = [
    { id: 'landing', label: 'Home', icon: Home },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'ai-recommendations', label: 'AI Trainer', icon: Brain },
    { id: 'profile', label: 'Profile', icon: User },
  ];

  const handleNavigation = (pageId: string) => {
    setCurrentPage(pageId);
    setIsOpen(false);
    // In a real app, this would use React Router
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-border shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Dumbbell className="h-8 w-8 text-[--fitness-primary]" />
            <span className="text-xl font-bold text-foreground">Formava AI</span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigation(item.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md transition-colors ${
                    currentPage === item.id
                      ? 'bg-[--fitness-primary] text-white'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
            <Button 
              variant="outline" 
              onClick={() => handleNavigation('login')}
              className="flex items-center gap-2"
            >
              <LogIn className="h-4 w-4" />
              Login
            </Button>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsOpen(!isOpen)}
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden border-t border-border">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavigation(item.id)}
                    className={`flex items-center gap-3 w-full px-3 py-2 rounded-md transition-colors ${
                      currentPage === item.id
                        ? 'bg-[--fitness-primary] text-white'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </button>
                );
              })}
              <Button 
                variant="outline" 
                onClick={() => handleNavigation('login')}
                className="w-full justify-start gap-3 mt-2"
              >
                <LogIn className="h-5 w-5" />
                Login
              </Button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}