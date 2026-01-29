import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface AuditLog {
  id: string;
  user_id?: string;
  action_type: string;
  resource_type?: string;
  resource_id?: string;
  before_state?: Record<string, any>;
  after_state?: Record<string, any>;
  details?: Record<string, any>;
  created_at: string;
}

export const AuditLogViewer: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState('');
  const [filterUserId, setFilterUserId] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  useEffect(() => {
    fetchAuditLogs();
  }, [filterAction, filterUserId]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string> = {};
      if (filterAction) params.action_type = filterAction;
      if (filterUserId) params.user_id = filterUserId;

      const response = await axios.get(
        `/api/audit-logs`,
        {
          params,
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      setLogs(response.data.logs || []);
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to fetch audit logs';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const getActionBadgeColor = (action: string) => {
    const actions: Record<string, { bg: string; text: string }> = {
      'CLAIM_DOCUMENT': { bg: 'bg-blue-100', text: 'text-blue-800' },
      'APPROVE_DOCUMENT': { bg: 'bg-green-100', text: 'text-green-800' },
      'REJECT_DOCUMENT': { bg: 'bg-red-100', text: 'text-red-800' },
      'VIEW_DOCUMENT': { bg: 'bg-gray-100', text: 'text-gray-800' },
      'CLASSIFY_DOCUMENT': { bg: 'bg-purple-100', text: 'text-purple-800' },
    };
    const colors = actions[action] || { bg: 'bg-gray-100', text: 'text-gray-800' };
    return colors;
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
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="mt-2 text-gray-600">System activity and user actions</p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Filter by user ID..."
            value={filterUserId}
            onChange={(e) => setFilterUserId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
          />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
          >
            <option value="">All Actions</option>
            <option value="CLAIM_DOCUMENT">Claim Document</option>
            <option value="APPROVE_DOCUMENT">Approve Document</option>
            <option value="REJECT_DOCUMENT">Reject Document</option>
            <option value="VIEW_DOCUMENT">View Document</option>
            <option value="CLASSIFY_DOCUMENT">Classify Document</option>
          </select>
        </div>

        {logs.length === 0 ? (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-blue-800">No audit logs found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto border rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Action</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Resource</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Timestamp</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">Details</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log) => {
                  const colors = getActionBadgeColor(log.action_type);
                  return (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm">
                        <span className={`${colors.bg} ${colors.text} px-3 py-1 rounded-full text-sm font-medium`}>
                          {log.action_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">{log.user_id || '-'}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {log.resource_type ? `${log.resource_type}:${log.resource_id}` : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="text-blue-600 hover:text-blue-900 font-medium"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center p-6 border-b sticky top-0 bg-white">
              <h2 className="text-xl font-bold text-gray-900">Audit Log Details</h2>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-500 hover:text-gray-700 font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-gray-700 mb-2">Action</h3>
                <p className="text-gray-900">{selectedLog.action_type}</p>
              </div>

              {selectedLog.user_id && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">User ID</h3>
                  <p className="text-gray-900">{selectedLog.user_id}</p>
                </div>
              )}

              {selectedLog.resource_type && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">Resource</h3>
                  <p className="text-gray-900">{selectedLog.resource_type}: {selectedLog.resource_id}</p>
                </div>
              )}

              {selectedLog.before_state && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">Before State</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.before_state, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.after_state && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">After State</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.after_state, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.details && (
                <div>
                  <h3 className="text-sm font-bold text-gray-700 mb-2">Details</h3>
                  <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <h3 className="text-sm font-bold text-gray-700 mb-2">Timestamp</h3>
                <p className="text-gray-900">{new Date(selectedLog.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="flex justify-end p-6 border-t">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
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
