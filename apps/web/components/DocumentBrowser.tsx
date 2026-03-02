/**
 * Document Browser
 * 
 * Browse, search, and view documents stored in the system.
 * Provides document retrieval experience with:
 * - Paginated document listing
 * - Search and filtering
 * - Document viewer with OCR text and metadata
 * - Version history
 * - Download and export options
 */

'use client';

import { useCallback, useEffect, useState } from 'react';

interface StoredDocument {
  content_id: string;
  backend: string;
  size: number;
  hash: string;
  version: number;
  created_at: string;
  metadata?: {
    job_id?: string;
    file_index?: number;
    original_file_path?: string;
    document?: {
      type?: string;
      title?: string;
      date?: {
        display?: string;
      };
    };
    content?: {
      summary?: string;
    };
  };
}

interface EnrichedMetadata {
  document?: {
    type?: string;
    title?: string;
    date?: {
      display?: string;
    };
    language?: string;
  };
  content?: {
    summary?: string;
    keywords?: string[];
  };
  people?: Array<{
    name: string;
    role?: string;
    biography?: string;
  }>;
}

interface StorageStats {
  total_items: number;
  total_size: number;
}

interface DocumentContent {
  ocr_text: string;
  enriched_metadata: EnrichedMetadata;
  storage_metadata: {
    content_id: string;
    backend: string;
    size: number;
    hash: string;
    version: number;
    created_at: string;
  };
}

interface DocumentBrowserProps {
  wsUrl: string;
  connected: boolean;
  send: (method: string, params: any) => Promise<any>;
}

export default function DocumentBrowser({ wsUrl, connected, send }: DocumentBrowserProps) {
  const unwrapMcpResult = (payload: any) => {
    let current = payload;
    let depth = 0;
    while (current && typeof current === 'object' && 'result' in current && depth < 6) {
      const next = current.result;
      if (next === undefined) {
        break;
      }
      current = next;
      depth += 1;
    }
    return current || {};
  };

  // State
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Debug: log loaded documents
  useEffect(() => {
    if (documents.length > 0) {
      // eslint-disable-next-line no-console
      console.log('Loaded documents:', documents);
    }
  }, [documents]);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [hasMore, setHasMore] = useState(true);
  
  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [contentTypeFilter, setContentTypeFilter] = useState('');
  const [backendFilter, setBackendFilter] = useState('');
  
  // Stats
  const [stats, setStats] = useState<StorageStats | null>(null);

  // Load documents (always show all, then filter in UI)
  const loadDocuments = useCallback(async (reset = false) => {
    if (!connected) {
      setError('WebSocket not connected');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Always fetch all documents, ignore filters for now
      const result = await send('tools/invoke', {
        name: 'list_documents',
        agentId: 'storage-agent',
        arguments: { limit: 1000, offset: 0 }
      }) as any;
      const data = unwrapMcpResult(result);
      const items = Array.isArray(data.items)
        ? data.items
        : Array.isArray(data.documents)
          ? data.documents
          : [];
      setDocuments(
        items.map((item: any) => ({
          ...item,
          content_id: item.content_id || item.id || '',
          backend: item.backend || item.backend_name || '',
          size: Number(item.size || item.file_size || 0),
          version: Number(item.version || 0),
          hash: item.file_hash || item.hash || '', // map file_hash to hash
        }))
      );
      setHasMore(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load documents';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [backendFilter, connected, contentTypeFilter, limit, page, send]);

  // Load stats
  const loadStats = async () => {
    if (!connected) return;
    
    try {
      const result = await send('tools/invoke', {
        name: 'get_stats',
        agentId: 'storage-agent',
        arguments: {}
      }) as any;
      const data = unwrapMcpResult(result);
      const totalItems = Number(data.total_items ?? data.count ?? 0);
      const totalSize = Number(data.total_size ?? data.size ?? 0);
      setStats({
        total_items: Number.isFinite(totalItems) ? totalItems : 0,
        total_size: Number.isFinite(totalSize) ? totalSize : 0,
      });
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const handleClearAllDocuments = async () => {
    if (!window.confirm('Are you sure you want to delete ALL documents? This cannot be undone.')) {
      return;
    }

    setError(null);
    setDocuments([]);
    setSelectedDocument(null);
    setStats({ total_items: 0, total_size: 0 });

    try {
      const response = await send('tools/invoke', {
        name: 'delete_all_documents',
        agentId: 'storage-agent',
        arguments: {}
      }) as any;

      if (response?.success === false) {
        throw new Error(response?.error || 'Failed to clear documents');
      }

      await Promise.all([loadDocuments(true), loadStats()]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to clear documents';
      setError(message);
      // eslint-disable-next-line no-alert
      alert('Failed to clear documents: ' + message);
    }
  };

  // View document (optional: show metadata in a modal or side panel)
  // For now, just highlight selected
  const viewDocument = (contentId: string) => {
    setSelectedDocument({
      storage_metadata: { content_id: contentId, backend: '', size: 0, hash: '', version: 0, created_at: '' },
      ocr_text: '',
      enriched_metadata: {},
    });
  };

  // Initial load
  useEffect(() => {
    if (connected) {
      loadDocuments(true);
      loadStats();
    }
  }, [backendFilter, connected, contentTypeFilter, loadDocuments]);

  // Load more
  const loadMore = () => {
    setPage(p => p + 1);
    loadDocuments(false);
  };

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Format date
  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="h-full flex bg-slate-50">
      {/* Sidebar - Document List */}
      <div className="w-96 border-r border-slate-200 bg-white flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-xl font-bold text-slate-900 mb-4">Document Browser</h2>
          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {/* Filters */}
          <div className="space-y-2">
            <select
              value={contentTypeFilter}
              onChange={(e) => setContentTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">All Types</option>
              <option value="document">Documents</option>
              <option value="image">Images</option>
              <option value="text">Text</option>
            </select>
            <select
              value={backendFilter}
              onChange={(e) => setBackendFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">All Backends</option>
              <option value="local">Local</option>
              <option value="sqlite">SQLite</option>
              <option value="s3">S3</option>
              <option value="gcs">GCS</option>
              <option value="azure">Azure</option>
            </select>
          </div>
          {/* Stats */}
          {stats && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-500">Total Docs</p>
                <p className="text-lg font-bold text-slate-900">{stats.total_items}</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs text-slate-500">Total Size</p>
                <p className="text-lg font-bold text-slate-900">{formatSize(stats.total_size)}</p>
              </div>
            </div>
          )}
        </div>
        {/* Document List */}
        <div className="flex-1 overflow-y-auto">
          {loading && documents.length === 0 && (
            <div className="p-6 text-center text-slate-500">Loading...</div>
          )}
          {error && (
            <div className="p-6 text-center text-red-600 text-sm">{error}</div>
          )}
          {documents.length === 0 && !loading && (
            <div className="p-6 text-center text-slate-500 text-sm">No documents found</div>
          )}
          <div className="p-4 space-y-2">
            {documents
              .filter(doc => {
                // Apply search and filter after all docs are loaded
                // Removed content_type filter as StoredDocument does not have this property
                if (backendFilter && doc.backend !== backendFilter) return false;
                if (!searchQuery) return true;
                const title = doc.metadata?.document?.title || '';
                const path = doc.metadata?.original_file_path || '';
                const fallback = doc.content_id + (doc.backend || '') + (doc.hash || '');
                return (
                  title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  path.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  fallback.toLowerCase().includes(searchQuery.toLowerCase())
                );
              })
              .map((doc) => (
                <button
                  key={doc.content_id}
                  onClick={() => viewDocument(doc.content_id)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedDocument?.storage_metadata.content_id === doc.content_id
                      ? 'bg-blue-50 border-blue-200'
                      : 'bg-white border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-medium text-slate-900 text-sm line-clamp-1">
                      {doc.metadata?.document?.title || doc.metadata?.original_file_path || doc.content_id || 'Untitled Document'}
                    </h3>
                    <span className="text-xs text-slate-500 ml-2">{formatSize(doc.size)}</span>
                  </div>
                  {!doc.metadata?.document?.title && doc.metadata?.original_file_path && (
                    <p className="text-xs text-slate-500 mb-1">
                      📄 {doc.metadata.original_file_path}
                    </p>
                  )}
                  {doc.metadata?.document?.date?.display && (
                    <p className="text-xs text-slate-500 mb-1">
                      📅 {doc.metadata.document.date.display}
                    </p>
                  )}
                  {doc.metadata?.content?.summary && (
                    <p className="text-xs text-slate-600 line-clamp-2 mb-2">
                      {doc.metadata.content.summary}
                    </p>
                  )}
                </button>
              ))}
          </div>
        </div>
        {/* Clear All Button */}
        <div className="p-4 border-t border-slate-200">
          <button
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm"
            onClick={handleClearAllDocuments}
          >
            🗑️ Clear All Documents
          </button>
        </div>
      </div>
      {/* Main Content - Document Viewer */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {selectedDocument ? (
          <>
            {/* Summary */}
            {selectedDocument.enriched_metadata?.content?.summary && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <h3 className="font-semibold text-blue-900 mb-2">Summary</h3>
                <p className="text-sm text-blue-800">
                  {selectedDocument.enriched_metadata.content.summary}
                </p>
              </div>
            )}
            {/* OCR Text */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Extracted Text</h3>
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 leading-relaxed">
                  {selectedDocument.ocr_text}
                </pre>
              </div>
            </div>
            {/* Metadata */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Metadata</h3>
              {/* People */}
              {selectedDocument.enriched_metadata?.people && selectedDocument.enriched_metadata.people.length > 0 && (
                <div className="mb-6">
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">People</h4>
                  <div className="space-y-3">
                    {selectedDocument.enriched_metadata.people.map((person, index) => (
                      <div key={index} className="bg-slate-50 rounded-lg p-3">
                        <p className="font-medium text-slate-900">{person.name}</p>
                        {person.role && <p className="text-sm text-slate-600">{person.role}</p>}
                        {person.biography && <p className="text-xs text-slate-500 mt-1">{person.biography}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Keywords */}
              {selectedDocument.enriched_metadata?.content?.keywords && (
                <div className="mb-6">
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">Keywords</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedDocument.enriched_metadata.content.keywords.map((keyword: string, index: number) => (
                      <span key={index} className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {/* Full Metadata JSON */}
              <details className="mt-6">
                <summary className="cursor-pointer text-sm font-medium text-slate-700 hover:text-slate-900">
                  View Full Metadata JSON
                </summary>
                <pre className="mt-3 p-4 bg-slate-900 text-slate-100 text-xs rounded-lg overflow-x-auto">
                  {JSON.stringify(selectedDocument.enriched_metadata, null, 2)}
                </pre>
              </details>
            </div>
            {/* Storage Info */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Storage Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Content ID</p>
                  <p className="text-sm font-mono text-slate-900">{selectedDocument.storage_metadata.content_id}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Backend</p>
                  <p className="text-sm text-slate-900">{selectedDocument.storage_metadata.backend}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Size</p>
                  <p className="text-sm text-slate-900">{formatSize(selectedDocument.storage_metadata.size)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Version</p>
                  <p className="text-sm text-slate-900">v{selectedDocument.storage_metadata.version}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Hash</p>
                  <p className="text-sm font-mono text-slate-900 truncate">{selectedDocument.storage_metadata.hash}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Created</p>
                  <p className="text-sm text-slate-900">{formatDate(selectedDocument.storage_metadata.created_at)}</p>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
      </div>
  );
}
