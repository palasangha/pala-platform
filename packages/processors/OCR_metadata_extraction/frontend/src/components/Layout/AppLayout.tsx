import React from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import PageNavigation from '@/components/Navigation/PageNavigation';
import Breadcrumbs from '@/components/Navigation/Breadcrumbs';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const handleLogout = () => {
    clearAuth();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50 flex flex-col">
      {/* Navigation Header */}
      <PageNavigation onLogout={handleLogout} />

      {/* Breadcrumbs */}
      <Breadcrumbs />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        <div className="space-y-6">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-6 px-6 mt-12 border-t border-slate-700">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm">
          <div>
            <p className="font-medium text-slate-300">Doc GenAI</p>
            <p className="text-xs">AI-Powered Document Intelligence Platform</p>
          </div>
          <div className="text-right">
            <p className="text-xs">&copy; 2025 Doc GenAI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
