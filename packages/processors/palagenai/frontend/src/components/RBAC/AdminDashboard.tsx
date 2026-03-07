import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { Search, Filter, RefreshCw } from 'lucide-react';

interface DashboardOverview {
  total_documents: number;
  classification_pending: number;
  classified: number;
  ocr_processing: number;
  ocr_processed: number;
  in_review: number;
  approved: number;
  rejected: number;
  exported: number;
  pending: number;
  average_review_time: number;
  progress_percentage: number;
}

interface DashboardStats {
  status: string;
  total_documents: number;
  in_review: number;
  approved: number;
  rejected: number;
  pending: number;
  average_review_time: number;
  overview: DashboardOverview;
  status_breakdown: Record<string, number>;
  bottleneck: {
    stage: string | null;
    count: number;
    recommendation: string;
  };
}

interface Document {
  id: string;
  original_filename: string;
  review_status: string;
  classification: string;
  reviewed_by_role?: string;
  reviewed_by_name?: string;
  created_at: string;
}

interface DocumentsResponse {
  documents: Document[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export const AdminDashboard: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoading, setDocsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchDashboard();
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter, searchQuery, page]);

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

  const fetchDocuments = async () => {
    try {
      setDocsLoading(true);

      const params: Record<string, string | number> = {
        page,
        per_page: 20
      };
      if (statusFilter) params.status = statusFilter;
      if (searchQuery) params.search = searchQuery;

      const response = await axios.get<DocumentsResponse>(
        `/api/rbac/documents`,
        {
          params,
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setDocuments(response.data.documents);
      setTotalPages(response.data.total_pages);
      setTotal(response.data.total);
    } catch (err: any) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setDocsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchDocuments();
  };

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, { bg: string; text: string; label: string }> = {
      'in_review': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'In Review' },
      'approved': { bg: 'bg-green-100', text: 'text-green-800', label: 'Approved' },
      'rejected': { bg: 'bg-red-100', text: 'text-red-800', label: 'Rejected' }
    };
    const style = statusStyles[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status || 'Unknown' };
    return (
      <span className={`${style.bg} ${style.text} px-3 py-1 rounded-full text-sm font-medium`}>
        {style.label}
      </span>
    );
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
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <StatCard label="Total Documents" value={stats.total_documents || 0} />
              <StatCard label="In Review" value={stats.in_review || 0} subtext="Awaiting reviewer action" />
              <StatCard label="Approved" value={stats.approved || 0} subtext="Successfully reviewed" />
              <StatCard label="Rejected" value={stats.rejected || 0} subtext="Sent back for revision" />
              <StatCard label="Pending" value={stats.pending || 0} subtext="Waiting for processing" />
              <StatCard
                label="Avg Review Time"
                value={stats.average_review_time > 0 ? `${Math.round(stats.average_review_time)}m` : 'N/A'}
                subtext="Minutes per document"
              />
            </div>

            {stats.bottleneck && stats.bottleneck.stage && (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">Bottleneck Detected</h3>
                    <div className="mt-2 text-sm text-yellow-700">
                      <p><strong>{stats.bottleneck.count}</strong> documents stuck at <strong>{stats.bottleneck.stage}</strong> stage</p>
                      <p className="mt-1">{stats.bottleneck.recommendation}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {stats.overview && stats.overview.progress_percentage !== undefined && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Processing Progress</h3>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                    style={{ width: `${stats.overview.progress_percentage}%` }}
                  ></div>
                </div>
                <p className="text-sm text-gray-600 mt-2 text-center">
                  {stats.overview.progress_percentage}% complete ({stats.approved + (stats.overview?.exported || 0)} / {stats.total_documents})
                </p>
              </div>
            )}
          </>
        )}

        <div className="flex gap-3 pt-4">
          <button
            onClick={() => { fetchDashboard(); fetchDocuments(); }}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {/* Document Table Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-4">All Documents</h3>
            
            {/* Filters and Search */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex items-center gap-2">
                <Filter size={16} className="text-gray-500" />
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="in_review">In Review</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              
              <form onSubmit={handleSearch} className="flex-1 flex gap-2">
                <div className="relative flex-1">
                  <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by document name..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                >
                  Search
                </button>
              </form>
            </div>
          </div>

          {/* Documents Table */}
          <div className="overflow-x-auto">
            {docsLoading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No documents found</div>
            ) : (
              <table className="w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">S.No</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Document File Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Document Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Reviewed By (Role / User)</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc, index) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-500">{(page - 1) * 20 + index + 1}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-xs" title={doc.original_filename}>
                        {doc.original_filename}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {getStatusBadge(doc.review_status)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {doc.reviewed_by_role && (
                          <span className={`font-medium ${doc.reviewed_by_role === 'Teacher' ? 'text-green-600' : 'text-blue-600'}`}>
                            {doc.reviewed_by_role}
                          </span>
                        )}
                        {doc.reviewed_by_name && (
                          <span className="text-gray-500 ml-1">({doc.reviewed_by_name})</span>
                        )}
                        {!doc.reviewed_by_role && !doc.reviewed_by_name && (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center p-4 border-t border-gray-200">
              <span className="text-sm text-gray-600">
                Showing {(page - 1) * 20 + 1} - {Math.min(page * 20, total)} of {total} documents
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm">Page {page} of {totalPages}</span>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
