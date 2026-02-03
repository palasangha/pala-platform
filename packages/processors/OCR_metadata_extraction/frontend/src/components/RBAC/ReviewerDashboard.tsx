import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { Search, Filter, RefreshCw, FileText } from 'lucide-react';

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

export const ReviewerDashboard: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter, searchQuery, page]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);

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
      const message = err.response?.data?.error || 'Failed to fetch documents';
      setError(message);
    } finally {
      setLoading(false);
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

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <FileText className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Reviewer Dashboard</h1>
            <p className="text-gray-600">Public documents assigned for review</p>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Document Table Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
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

              <button
                onClick={fetchDocuments}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
              >
                <RefreshCw size={16} />
                Refresh
              </button>
            </div>
          </div>

          {/* Documents Table */}
          <div className="overflow-x-auto">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No public documents found</div>
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
                        <span className="font-medium text-blue-600">Reviewer</span>
                        {doc.reviewed_by_name && (
                          <span className="text-gray-500 ml-1">({doc.reviewed_by_name})</span>
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

export default ReviewerDashboard;
