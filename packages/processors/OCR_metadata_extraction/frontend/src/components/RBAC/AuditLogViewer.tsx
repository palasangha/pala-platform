import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { History, RotateCcw, X, Filter } from 'lucide-react';

interface AuditLog {
  id: string;
  user_id?: string;
  action_type: string;
  resource_type?: string;
  resource_id?: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  details?: Record<string, any>;
  created_at: string;
  // Enriched fields from backend
  document_name?: string;
  document_status?: string;
  changed_by_name?: string;
  changed_by_role?: string;
}

interface PaginationData {
  page: number;
  per_page: number;
  total_count: number;
  total_pages: number;
}

export const AuditLogViewer: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<PaginationData>({
    page: 1,
    per_page: 50,
    total_count: 0,
    total_pages: 0
  });

  useEffect(() => {
    fetchAuditLogs();
  }, [filterAction, page]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number> = { page, per_page: 50 };
      if (filterAction) params.action_type = filterAction;

      const response = await axios.get(
        `/api/rbac/audit-logs`,
        {
          params,
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setLogs(response.data.audit_logs || []);
      setPagination(response.data.pagination || {
        page: 1,
        per_page: 50,
        total_count: 0,
        total_pages: 0
      });
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to fetch audit logs';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (logId: string) => {
    try {
      setRestoring(true);
      setError(null);

      await axios.post(
        `/api/rbac/audit-logs/${logId}/restore`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setSuccess('Document restored successfully');
      setSelectedLog(null);
      fetchAuditLogs();

      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to restore document';
      setError(message);
    } finally {
      setRestoring(false);
    }
  };

  const getActionBadgeColor = (action: string) => {
    const actions: Record<string, { bg: string; text: string; label: string }> = {
      'CREATE': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Create' },
      'EDIT': { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Edit' },
      'DELETE': { bg: 'bg-red-100', text: 'text-red-800', label: 'Delete' },
      'APPROVE_DOCUMENT': { bg: 'bg-green-100', text: 'text-green-800', label: 'Approve' },
      'REJECT_DOCUMENT': { bg: 'bg-red-100', text: 'text-red-800', label: 'Reject' },
      'RESTORE': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Restore' },
      'CLAIM_DOCUMENT': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Claim' },
      'CLASSIFY_DOCUMENT': { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Classify' },
    };
    return actions[action] || { bg: 'bg-gray-100', text: 'text-gray-800', label: action };
  };

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, { bg: string; text: string; label: string }> = {
      'in_review': { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'In Review' },
      'approved': { bg: 'bg-green-100', text: 'text-green-800', label: 'Approved' },
      'rejected': { bg: 'bg-red-100', text: 'text-red-800', label: 'Rejected' }
    };
    const style = statusStyles[status] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status || 'Unknown' };
    return (
      <span className={`${style.bg} ${style.text} px-2 py-0.5 rounded-full text-xs font-medium`}>
        {style.label}
      </span>
    );
  };

  if (loading && logs.length === 0) {
    return (
      <div className="max-w-7xl mx-auto py-8">
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <History className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
            <p className="text-gray-600">Document activity and version history</p>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {success && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-md">
            <p className="text-green-800">{success}</p>
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-gray-500" />
            <select
              value={filterAction}
              onChange={(e) => { setFilterAction(e.target.value); setPage(1); }}
              className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Actions</option>
              <option value="CREATE">Create</option>
              <option value="EDIT">Edit</option>
              <option value="DELETE">Delete</option>
              <option value="APPROVE_DOCUMENT">Approve</option>
              <option value="REJECT_DOCUMENT">Reject</option>
              <option value="RESTORE">Restore</option>
            </select>
          </div>
        </div>

        {logs.length === 0 ? (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-blue-800">No audit logs found.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">S.No</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Document Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Document Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Changed By</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Action Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log, index) => {
                    const actionStyle = getActionBadgeColor(log.action_type);
                    return (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-500">{(page - 1) * 50 + index + 1}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 truncate max-w-xs">
                          {log.document_name || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {log.document_status ? getStatusBadge(log.document_status) : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {log.changed_by_name && (
                            <div>
                              <span className="font-medium">{log.changed_by_name}</span>
                              {log.changed_by_role && (
                                <span className="text-gray-500 text-xs ml-1">({log.changed_by_role})</span>
                              )}
                            </div>
                          )}
                          {!log.changed_by_name && <span className="text-gray-400">-</span>}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`${actionStyle.bg} ${actionStyle.text} px-2 py-1 rounded-full text-xs font-medium`}>
                            {actionStyle.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm space-x-2">
                          <button
                            onClick={() => setSelectedLog(log)}
                            className="text-indigo-600 hover:text-indigo-900 font-medium"
                          >
                            View
                          </button>
                          {log.previous_state && (
                            <button
                              onClick={() => handleRestore(log.id)}
                              disabled={restoring}
                              className="text-yellow-600 hover:text-yellow-900 font-medium disabled:opacity-50"
                            >
                              <RotateCcw size={14} className="inline mr-1" />
                              Restore
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination.total_pages > 1 && (
              <div className="flex justify-between items-center p-4 border-t border-gray-200">
                <span className="text-sm text-gray-600">
                  Showing {(page - 1) * 50 + 1} - {Math.min(page * 50, pagination.total_count)} of {pagination.total_count}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1 text-sm">Page {page} of {pagination.total_pages}</span>
                  <button
                    onClick={() => setPage(Math.min(pagination.total_pages, page + 1))}
                    disabled={page === pagination.total_pages}
                    className="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white">
              <h2 className="text-xl font-bold text-gray-900">Audit Log Details</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-1">Action</h3>
                  <p className="text-gray-900">{selectedLog.action_type}</p>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-1">Timestamp</h3>
                  <p className="text-gray-900">{new Date(selectedLog.created_at).toLocaleString()}</p>
                </div>
              </div>

              {selectedLog.document_name && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-1">Document</h3>
                  <p className="text-gray-900">{selectedLog.document_name}</p>
                </div>
              )}

              {selectedLog.changed_by_name && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-1">Changed By</h3>
                  <p className="text-gray-900">{selectedLog.changed_by_name} ({selectedLog.changed_by_role})</p>
                </div>
              )}

              {selectedLog.previous_state && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">Previous State</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.previous_state, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.new_state && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">New State</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.new_state, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">Details</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex gap-3 justify-end p-6 border-t">
              {selectedLog.previous_state && (
                <button
                  onClick={() => handleRestore(selectedLog.id)}
                  disabled={restoring}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <RotateCcw size={16} />
                  {restoring ? 'Restoring...' : 'Restore to This Version'}
                </button>
              )}
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogViewer;
