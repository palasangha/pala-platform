import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FolderOpen, Zap, Database, Activity, Layers, LogOut, Settings, Home, Link2, BarChart, CheckSquare, FileText, Boxes, Edit, ChevronDown, Users } from 'lucide-react';

export const PageNavigation: React.FC<{ onLogout?: () => void }> = ({ onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [rbacDropdownOpen, setRbacDropdownOpen] = useState(false);

  const navItems = [
    { path: '/projects', label: 'Projects', icon: FolderOpen },
    { path: '/bulk', label: 'Bulk OCR', icon: Zap },
    { path: '/ocr-chains', label: 'OCR Chains', icon: Link2 },
    { path: '/archipelago-raw-uploader', label: 'Archipelago Upload', icon: Database },
    { path: '/workers', label: 'Workers', icon: Activity },
    { path: '/supervisor', label: 'Supervisor', icon: Layers },
    { path: '/swarm', label: 'Swarm', icon: Boxes },
  ];

  const rbacItems = [
    { path: '/rbac/admin-dashboard', label: 'Dashboard', icon: BarChart },
    { path: '/rbac/review-queue', label: 'Review Queue', icon: CheckSquare },
    { path: '/rbac/audit-logs', label: 'Audit Logs', icon: FileText },
    { path: '/rbac/user-roles', label: 'User Roles', icon: Users },
    { path: '/archipelago-metadata-updater', label: 'Metadata Update', icon: Edit },
  ];

  const isActive = (path: string) => location.pathname === path;
  const isRbacActive = rbacItems.some(item => isActive(item.path));

  return (
    <div className="bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-6">
        {/* Top Bar */}
        <div className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-md">
              <Home className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Doc GenAI</h1>
              <p className="text-xs text-slate-400">AI-Powered Document Intelligence</p>
            </div>
          </div>
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-all duration-200 font-medium shadow-md hover:shadow-lg"
            >
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
          )}
        </div>

        {/* Navigation Menu */}
        <nav className="flex gap-1 py-0 flex-wrap items-center">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex items-center gap-2 px-4 py-3 transition-all duration-200 font-medium whitespace-nowrap border-b-2 ${
                  active
                    ? 'bg-slate-700 text-blue-400 border-b-2 border-blue-500 shadow-md'
                    : 'text-slate-300 hover:text-white border-b-2 border-transparent hover:bg-slate-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </button>
            );
          })}

          {/* RBAC Dropdown Menu */}
          <div className="relative">
            <button
              onClick={() => setRbacDropdownOpen(!rbacDropdownOpen)}
              className={`flex items-center gap-2 px-4 py-3 transition-all duration-200 font-medium whitespace-nowrap border-b-2 ${
                isRbacActive || rbacDropdownOpen
                  ? 'bg-slate-700 text-purple-400 border-b-2 border-purple-500 shadow-md'
                  : 'text-slate-300 hover:text-white border-b-2 border-transparent hover:bg-slate-700'
              }`}
            >
              <BarChart className="w-4 h-4" />
              <span>RBAC</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${rbacDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {rbacDropdownOpen && (
              <div className="absolute top-full left-0 mt-0 bg-slate-800 border border-slate-700 rounded-b-lg shadow-lg z-50 min-w-48">
                {rbacItems.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.path);
                  return (
                    <button
                      key={item.path}
                      onClick={() => {
                        navigate(item.path);
                        setRbacDropdownOpen(false);
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2 transition-all duration-200 font-medium border-l-2 ${
                        active
                          ? 'bg-slate-700 text-purple-400 border-l-purple-500 border-l-2'
                          : 'text-slate-300 hover:text-white hover:bg-slate-700 border-l-transparent'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Settings Button - Always at the end */}
          <div className="ml-auto">
            <button
              onClick={() => navigate('/system-settings')}
              className={`flex items-center gap-2 px-4 py-3 transition-all duration-200 font-medium border-b-2 ${
                isActive('/system-settings')
                  ? 'bg-slate-700 text-amber-400 border-b-2 border-amber-500 shadow-md'
                  : 'text-slate-300 hover:text-white border-b-2 border-transparent hover:bg-slate-700'
              }`}
              title="System Settings and Configuration"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
          </div>
        </nav>
      </div>
    </div>
  );
};

export default PageNavigation;
