import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { Login } from '@/components/Auth/Login';
import { Register } from '@/components/Auth/Register';
import { AuthCallback } from '@/components/Auth/AuthCallback';
import { ProjectList } from '@/components/Projects/ProjectList';
import { ProjectDetail } from '@/components/Projects/ProjectDetail';
import { OCRReview } from '@/components/OCRPanel/OCRReview';
import { BulkOCRProcessor } from '@/components/BulkOCR';
import ArchipelagoRawUploader from "@/pages/ArchipelagoRawUploader";
import { WorkerMonitor } from '@/pages/WorkerMonitor';
import { SupervisorDashboard } from '@/pages/SupervisorDashboard';
import { SwarmDashboard } from '@/pages/SwarmDashboard';
import SystemSettings from '@/pages/SystemSettings';
import OCRChainBuilder from '@/pages/OCRChainBuilder';
import OCRChainResults from '@/pages/OCRChainResults';
import AppLayout from '@/components/Layout/AppLayout';

// RBAC Components
import { AdminDashboard } from '@/components/RBAC/AdminDashboard';
import { ReviewQueue } from '@/components/RBAC/ReviewQueue';
import { AuditLogViewer } from '@/components/RBAC/AuditLogViewer';
import { UserRoleManagement } from '@/components/RBAC/UserRoleManagement';

// Archipelago Metadata Updater
import { ArchipelagoMetadataUpdater } from '@/pages/ArchipelagoMetadataUpdater';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

// Public Route Component (redirects to projects if already authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/projects" replace />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <Register />
              </PublicRoute>
            }
          />
          <Route path="/auth/callback" element={<AuthCallback />} />

          {/* Protected Routes */}
          <Route
            path="/projects"
            element={
              <ProtectedRoute>
                <ProjectList />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId"
            element={
              <ProtectedRoute>
                <ProjectDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/images/:imageId"
            element={
              <ProtectedRoute>
                <OCRReview />
              </ProtectedRoute>
            }
          />
          <Route
            path="/bulk"
            element={
              <ProtectedRoute>
                <BulkOCRProcessor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ocr-chains"
            element={
              <ProtectedRoute>
                <OCRChainBuilder />
              </ProtectedRoute>
            }
          />
          <Route
            path="/ocr-chains/results/:jobId"
            element={
              <ProtectedRoute>
                <OCRChainResults />
              </ProtectedRoute>
            }
          />
          <Route
            path="/archipelago-raw-uploader"
            element={
              <ProtectedRoute>
                <ArchipelagoRawUploader />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workers"
            element={
              <ProtectedRoute>
                <WorkerMonitor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/supervisor"
            element={
              <ProtectedRoute>
                <SupervisorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/swarm"
            element={
              <ProtectedRoute>
                <SwarmDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/system-settings"
            element={
              <ProtectedRoute>
                <SystemSettings />
              </ProtectedRoute>
            }
          />

          {/* RBAC Routes */}
          <Route
            path="/rbac/admin-dashboard"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rbac/review-queue"
            element={
              <ProtectedRoute>
                <ReviewQueue />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rbac/audit-logs"
            element={
              <ProtectedRoute>
                <AuditLogViewer />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rbac/user-roles"
            element={
              <ProtectedRoute>
                <UserRoleManagement />
              </ProtectedRoute>
            }
          />

          {/* Archipelago Metadata Updater Route */}
          <Route
            path="/archipelago-metadata-updater"
            element={
              <ProtectedRoute>
                <ArchipelagoMetadataUpdater />
              </ProtectedRoute>
            }
          />

          {/* Default Route */}
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
