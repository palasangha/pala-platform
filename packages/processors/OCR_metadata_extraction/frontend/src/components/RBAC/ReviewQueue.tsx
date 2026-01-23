import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface Document {
  id: string;
  original_filename: string;
  classification: string;
  document_status: string;
  review_status?: string;
  claimed_by?: string;
  created_at: string;
}

interface PaginationData {
  page: number;
  per_page: number;
  total_count: number;
  total_pages: number;
}

interface ReviewQueueResponse {
  status: string;
  queue: Document[];
  pagination: PaginationData;
}

export const ReviewQueue: React.FC = () => {
  const { accessToken, user } = useAuthStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<PaginationData>({
    page: 1,
    per_page: 10,
    total_count: 0,
    total_pages: 0
  });
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Fetch review queue
  useEffect(() => {
    fetchReviewQueue();
  }, [pagination.page]);

  const fetchReviewQueue = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get<ReviewQueueResponse>(
        `/api/rbac/review-queue`,
        {
          params: {
            page: pagination.page,
            per_page: pagination.per_page
          },
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setDocuments(response.data.queue);
      setPagination(response.data.pagination);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to fetch review queue';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const claimDocument = async (docId: string) => {
    try {
      setActionInProgress(true);
      setError(null);

      await axios.post(
        `/api/rbac/review/${docId}/claim`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      // Refresh queue
      await fetchReviewQueue();
      setSelectedDoc(docId);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to claim document';
      setError(message);
    } finally {
      setActionInProgress(false);
    }
  };

  const approveDocument = async (docId: string, edits: Record<string, string> = {}, notes: string = '') => {
    try {
      setActionInProgress(true);
      setError(null);

      await axios.post(
        `/api/rbac/review/${docId}/approve`,
        {
          edit_fields: edits,
          notes: notes
        },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      // Refresh queue
      await fetchReviewQueue();
      setSelectedDoc(null);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to approve document';
      setError(message);
    } finally {
      setActionInProgress(false);
    }
  };

  const rejectDocument = async (docId: string, reason: string) => {
    try {
      setActionInProgress(true);
      setError(null);

      await axios.post(
        `/api/rbac/review/${docId}/reject`,
        { reason },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      // Refresh queue
      await fetchReviewQueue();
      setSelectedDoc(null);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to reject document';
      setError(message);
    } finally {
      setActionInProgress(false);
    }
  };

  const getClassificationBadge = (classification: string) => {
    const bgColor = classification === 'PUBLIC' ? 'bg-green-100' : 'bg-red-100';
    const textColor = classification === 'PUBLIC' ? 'text-green-800' : 'text-red-800';
    return (
      <span className={`${bgColor} ${textColor} px-3 py-1 rounded-full text-sm font-medium`}>
        {classification}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const statusColors: Record<string, { bg: string; text: string }> = {
      'OCR_PROCESSED': { bg: 'bg-blue-100', text: 'text-blue-800' },
      'IN_REVIEW': { bg: 'bg-yellow-100', text: 'text-yellow-800' },
      'REVIEWED_APPROVED': { bg: 'bg-green-100', text: 'text-green-800' },
      'REJECTED': { bg: 'bg-red-100', text: 'text-red-800' }
    };
    const colors = statusColors[status] || { bg: 'bg-gray-100', text: 'text-gray-800' };
    return (
      <span className={`${colors.bg} ${colors.text} px-3 py-1 rounded-full text-sm font-medium`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto py-8">
        <div className="flex flex-col items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-gray-600">Loading review queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Review Queue</h1>
          <p className="mt-2 text-gray-600">{documents.length} documents waiting for review</p>
        </div>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {documents.length === 0 ? (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-md">
            <p className="text-blue-800">No documents available for review at this time.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto border rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Filename</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Classification</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Claimed By</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900 truncate max-w-xs">{doc.original_filename}</td>
                      <td className="px-6 py-4 text-sm">{getClassificationBadge(doc.classification)}</td>
                      <td className="px-6 py-4 text-sm">{getStatusBadge(doc.document_status)}</td>
                      <td className={`px-6 py-4 text-sm font-medium ${doc.claimed_by ? 'text-red-600' : 'text-green-600'}`}>
                        {doc.claimed_by ? 'Claimed' : 'Available'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-sm space-x-2 flex">
                        {!doc.claimed_by && (
                          <button
                            onClick={() => claimDocument(doc.id)}
                            disabled={actionInProgress && selectedDoc === doc.id}
                            className="px-3 py-1 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {actionInProgress && selectedDoc === doc.id ? 'Claiming...' : 'Claim'}
                          </button>
                        )}
                        {doc.claimed_by && doc.claimed_by === user?.id && (
                          <>
                            <button
                              onClick={() => approveDocument(doc.id)}
                              disabled={actionInProgress && selectedDoc === doc.id}
                              className="px-3 py-1 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {actionInProgress && selectedDoc === doc.id ? 'Approving...' : 'Approve'}
                            </button>
                            <button
                              onClick={() => rejectDocument(doc.id, 'Quality issues')}
                              disabled={actionInProgress && selectedDoc === doc.id}
                              className="px-3 py-1 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {actionInProgress && selectedDoc === doc.id ? 'Rejecting...' : 'Reject'}
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination.total_pages > 1 && (
              <div className="flex justify-center mt-6 gap-2">
                <button
                  onClick={() => setPagination({...pagination, page: Math.max(1, pagination.page - 1)})}
                  disabled={pagination.page === 1}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>

                {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                  const pageNum = Math.max(1, pagination.page - 2) + i;
                  if (pageNum > pagination.total_pages) return null;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPagination({...pagination, page: pageNum})}
                      className={`px-4 py-2 rounded-md font-medium ${
                        pagination.page === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}

                <button
                  onClick={() => setPagination({...pagination, page: Math.min(pagination.total_pages, pagination.page + 1)})}
                  disabled={pagination.page === pagination.total_pages}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ReviewQueue;
