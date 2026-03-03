'use client';

import { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface StoredContent {
  document_id: string;
  type: string;
  original_file: string;
  file_format: string;
  created_by: string;
  created_at: string;
  version: number;
  processed_data?: Record<string, any>;
  metadata?: Record<string, any>;
  app_data?: Record<string, any>;
}

interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export function ContentBrowser() {
  const { client, connected } = useWebSocket();
  const [contents, setContents] = useState<StoredContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    pageSize: 20,
    total: 0,
  });
  const [filters, setFilters] = useState({
    createdBy: '',
    search: '',
    type: '',
  });
  const [selectedContent, setSelectedContent] = useState<StoredContent | null>(
    null
  );

  const fetchContent = useCallback(() => {
    if (!connected || !client) return;

    try {
      setLoading(true);
      setError(null);

      const params = {
        limit: pagination.pageSize,
        offset: (pagination.page - 1) * pagination.pageSize,
        ...(filters.type && { type: filters.type }),
        ...(filters.createdBy && { created_by: filters.createdBy }),
      };

      const request = {
        jsonrpc: '2.0',
        method: 'tools/invoke',
        params: {
          agentId: 'storage-agent',
          toolName: 'list_documents',
          arguments: params,
        },
        id: `list-${Date.now()}`,
      };

      console.log('Sending list_documents request:', request);
      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          
          // Response is triple-nested: result.result.result.documents
          const toolResult = response.result?.result?.result;
          if (toolResult?.documents !== undefined) {
            setContents(toolResult.documents);
            setPagination((p) => ({
              ...p,
              total: toolResult.total || toolResult.count || 0,
            }));
            setLoading(false);
          } else if (response.error) {
            setError(response.error.message || 'Failed to fetch documents');
            setLoading(false);
          } else {
            setError('Could not find documents in response');
            setLoading(false);
          }
          client.removeEventListener('message', handleMessage);
        } catch (e) {
          console.error('Failed to parse response:', e);
          setError('Failed to parse response');
          setLoading(false);
          client.removeEventListener('message', handleMessage);
        }
      };

      client.addEventListener('message', handleMessage);
      
      // Timeout after 5 seconds
      void setTimeout(() => {
        client.removeEventListener('message', handleMessage);
        setLoading(false);
      }, 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents');
      setLoading(false);
    }
  }, [connected, client, pagination.page, pagination.pageSize, filters]);

  useEffect(() => {
    fetchContent();
  }, [fetchContent]);

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">
          Stored Content
        </h2>
        <span className="text-sm text-slate-600">
          {pagination.total} items
        </span>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-700 rounded-lg">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Created By
          </label>
          <select
            value={filters.createdBy}
            onChange={(e) =>
              setFilters({ ...filters, createdBy: e.target.value })
            }
            className="w-full px-3 py-2 border border-slate-600 bg-slate-800 rounded-md text-sm text-slate-100"
          >
            <option value="">All Users</option>
            <option value="ocr-agent">OCR Agent</option>
            <option value="content-agent">Content Agent</option>
            <option value="metadata-agent">Metadata Agent</option>
            <option value="user">User</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Document Type
          </label>
          <select
            value={filters.type}
            onChange={(e) =>
              setFilters({ ...filters, type: e.target.value })
            }
            className="w-full px-3 py-2 border border-slate-600 bg-slate-800 rounded-md text-sm text-slate-100"
          >
            <option value="">All Types</option>
            <option value="text">Text</option>
            <option value="image">Image</option>
            <option value="pdf">PDF</option>
            <option value="audio">Audio</option>
            <option value="video">Video</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Search
          </label>
          <input
            type="text"
            value={filters.search}
            onChange={(e) =>
              setFilters({ ...filters, search: e.target.value })
            }
            placeholder="Search filename..."
            className="w-full px-3 py-2 border border-slate-600 bg-slate-800 rounded-md text-sm text-slate-100"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Content Table */}
      <div className="border border-slate-600 rounded-lg overflow-hidden bg-slate-700">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 border-b border-slate-600">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Document ID
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Type
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Original File
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Created By
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Created
                </th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin h-5 w-5 text-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : contents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                    No documents found
                  </td>
                </tr>
              ) : (
                contents.map((content) => (
                  <tr
                    key={content.document_id}
                    className="border-b border-slate-600 hover:bg-slate-600"
                  >
                    <td className="px-4 py-2 font-mono text-xs text-slate-400">
                      {content.document_id.substring(0, 12)}...
                    </td>
                    <td className="px-4 py-2 text-slate-100">
                      <span className="inline-block px-2 py-1 bg-blue-900 text-blue-200 text-xs rounded">
                        {content.type}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-100 truncate">
                      {content.original_file || '—'}
                    </td>
                    <td className="px-4 py-2 text-slate-100">
                      <span className="inline-block px-2 py-1 bg-purple-900 text-purple-200 text-xs rounded">
                        {content.created_by}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-400">
                      {new Date(content.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={() => setSelectedContent(content)}
                        className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-600">
          Page {pagination.page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() =>
              setPagination((p) => ({
                ...p,
                page: Math.max(1, p.page - 1),
              }))
            }
            disabled={pagination.page === 1}
            className="px-3 py-1 border border-slate-300 rounded text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() =>
              setPagination((p) => ({
                ...p,
                page: Math.min(totalPages, p.page + 1),
              }))
            }
            disabled={pagination.page === totalPages}
            className="px-3 py-1 border border-slate-300 rounded text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedContent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">
                Document Details
              </h3>
              <button
                onClick={() => setSelectedContent(null)}
                className="text-slate-500 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-500">
                  Document ID
                </label>
                <p className="font-mono text-sm text-slate-900 break-all">
                  {selectedContent.document_id}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    Type
                  </label>
                  <p className="text-sm text-slate-900">
                    {selectedContent.type}
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    Created By
                  </label>
                  <p className="text-sm text-slate-900">
                    {selectedContent.created_by}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    Original File
                  </label>
                  <p className="text-sm text-slate-900 truncate">
                    {selectedContent.original_file || '—'}
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    File Format
                  </label>
                  <p className="text-sm text-slate-900">
                    {selectedContent.file_format || '—'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    Version
                  </label>
                  <p className="text-sm text-slate-900">
                    {selectedContent.version || '1'}
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">
                    Created At
                  </label>
                  <p className="text-sm text-slate-900">
                    {new Date(selectedContent.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {selectedContent.metadata && Object.keys(selectedContent.metadata).length > 0 && (
                <div className="bg-slate-50 p-3 rounded text-sm space-y-2">
                  <label className="text-xs font-medium text-slate-600">
                    Metadata
                  </label>
                  <pre className="text-xs text-slate-700 overflow-auto max-h-40 bg-white p-2 rounded border border-slate-200">
                    {JSON.stringify(selectedContent.metadata, null, 2)}
                  </pre>
                </div>
              )}

              {selectedContent.app_data && Object.keys(selectedContent.app_data).length > 0 && (
                <div className="bg-slate-50 p-3 rounded text-sm space-y-2">
                  <label className="text-xs font-medium text-slate-600">
                    App Data
                  </label>
                  <pre className="text-xs text-slate-700 overflow-auto max-h-40 bg-white p-2 rounded border border-slate-200">
                    {JSON.stringify(selectedContent.app_data, null, 2)}
                  </pre>
                </div>
              )}

              <div className="flex gap-2 pt-4">
                <button
                  onClick={() => setSelectedContent(null)}
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-900 hover:bg-slate-50"
                >
                  Close
                </button>
                <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                  Export
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
