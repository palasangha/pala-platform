import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface DashboardStats {
  total_documents: number;
  in_review: number;
  approved: number;
  rejected: number;
  pending: number;
  average_review_time: number;
}

export const AdminDashboard: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(
        `/api/dashboard/overview`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setStats(response.data);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to load dashboard';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto py-8">
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  const StatCard = ({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-gray-600 text-sm font-medium uppercase tracking-wide">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
      {subtext && <p className="text-sm text-gray-500 mt-1">{subtext}</p>}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="mt-2 text-gray-600">Overview of document processing and review metrics</p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <StatCard label="Total Documents" value={stats.total_documents} />
            <StatCard label="In Review" value={stats.in_review} subtext="Awaiting reviewer action" />
            <StatCard label="Approved" value={stats.approved} subtext="Successfully reviewed" />
            <StatCard label="Rejected" value={stats.rejected} subtext="Sent back for revision" />
            <StatCard label="Pending" value={stats.pending} subtext="Waiting for processing" />
            <StatCard
              label="Avg Review Time"
              value={`${Math.round(stats.average_review_time)}m`}
              subtext="Minutes per document"
            />
          </div>
        )}

        <div className="flex gap-3 pt-4">
          <button
            onClick={fetchDashboard}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
