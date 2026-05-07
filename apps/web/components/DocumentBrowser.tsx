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
  connected: boolean;
  send: (method: string, params: any) => Promise<any>;
  initialDocumentId?: string | null;
}

export default function DocumentBrowser({ connected, send, initialDocumentId }: DocumentBrowserProps) {
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
  const [documentDetails, setDocumentDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Debug: log loaded documents
  useEffect(() => {
    if (documents.length > 0) {
      // eslint-disable-next-line no-console
      console.log('Loaded documents:', documents);
    }
  }, [documents]);
  
  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [contentTypeFilter, setContentTypeFilter] = useState('');
  const [backendFilter, setBackendFilter] = useState('');
  
  // Stats
  const [stats, setStats] = useState<StorageStats | null>(null);

  // Load documents (always show all, then filter in UI)
  const loadDocuments = useCallback(async () => {
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
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load documents';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [backendFilter, connected, contentTypeFilter, send]);

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

      await Promise.all([loadDocuments(), loadStats()]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to clear documents';
      setError(message);
      // eslint-disable-next-line no-alert
      alert('Failed to clear documents: ' + message);
    }
  };

  // View document - retrieve full details from agent
  const viewDocument = (contentId: string) => {
    setLoadingDetails(true);
    console.log(`[DocumentBrowser] Retrieving details for document: ${contentId}`);
    
    send('tools/invoke', {
      name: 'retrieve_document',
      agentId: 'storage-agent',
      arguments: {
        document_id: contentId,
        include_original_file: false  // Don't download file yet, just metadata
      }
    })
    .then((response: any) => {
      console.log(`[DocumentBrowser] Retrieved document details:`, response);
      if (response?.result) {
        setDocumentDetails(response.result);
        setSelectedDocument({
          storage_metadata: {
            content_id: response.result.document_id,
            backend: response.result.provider_id || 'unknown',
            size: 0,
            hash: response.result.file_hash || '',
            version: response.result.version || 1,
            created_at: response.result.created_at || new Date().toISOString()
          },
          ocr_text: response.result.processed_data?.text || '',
          enriched_metadata: response.result.metadata || {}
        });
      } else {
        console.error('[DocumentBrowser] No result in response', response);
      }
    })
    .catch((err: any) => {
      console.error(`[DocumentBrowser] Failed to retrieve document details:`, err);
      alert(`Failed to load document: ${err.message || 'Unknown error'}`);
    })
    .finally(() => {
      setLoadingDetails(false);
    });
  };

  // Auto-load initial document if provided
  useEffect(() => {
    if (initialDocumentId && connected) {
      try {
        viewDocument(initialDocumentId);
      } catch (err) {
        console.error('[DocumentBrowser] Failed to auto-load initial document', err);
      }
    }
  }, [initialDocumentId, connected]);

  // Initial load
  useEffect(() => {
    if (connected) {
      loadDocuments();
      loadStats();
    }
  }, [backendFilter, connected, contentTypeFilter, loadDocuments]);

  // Download original document
  const downloadOriginalDocument = async (documentId: string, fileName: string) => {
    try {
      console.log(`[DocumentBrowser] Downloading original document: ${documentId}`);
      setLoadingDetails(true);
      
      const response = await send('tools/invoke', {
        name: 'retrieve_document',
        agentId: 'storage-agent',
        arguments: {
          document_id: documentId,
          include_original_file: true
        }
      }) as any;

      if (response?.result?.original_file_data) {
        console.log(`[DocumentBrowser] File data retrieved, size: ${response.result.original_file_size} bytes`);
        
        // Convert base64 to blob and download
        const binaryString = atob(response.result.original_file_data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: response.result.original_file_mime || 'application/octet-stream' });
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName || `document-${documentId}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        console.log(`[DocumentBrowser] File downloaded successfully: ${fileName}`);
      } else {
        console.error('[DocumentBrowser] No file data in response');
        alert('No file data available for download');
      }
    } catch (err: any) {
      console.error(`[DocumentBrowser] Failed to download document:`, err);
      alert(`Failed to download document: ${err.message || 'Unknown error'}`);
    } finally {
      setLoadingDetails(false);
    }
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
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">Storage Information</h3>
                {documentDetails?.original_file && (
                  <button
                    onClick={() => downloadOriginalDocument(
                      documentDetails.document_id,
                      documentDetails.original_file
                    )}
                    disabled={loadingDetails}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:bg-slate-400"
                  >
                    {loadingDetails ? 'Downloading...' : 'Download Original'}
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Document ID</p>
                  <p className="text-sm font-mono text-slate-900 break-all">{selectedDocument.storage_metadata.content_id}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Type</p>
                  <p className="text-sm text-slate-900">{documentDetails?.type || 'unknown'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Original File</p>
                  <p className="text-sm text-slate-900">{documentDetails?.original_file || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">File Format</p>
                  <p className="text-sm text-slate-900">{documentDetails?.file_format || 'unknown'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">File Hash</p>
                  <p className="text-sm font-mono text-slate-900 truncate">{documentDetails?.file_hash || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Provider</p>
                  <p className="text-sm text-slate-900">{selectedDocument.storage_metadata.backend}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Version</p>
                  <p className="text-sm text-slate-900">v{selectedDocument.storage_metadata.version}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Created By</p>
                  <p className="text-sm text-slate-900">{documentDetails?.created_by || 'unknown'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Created</p>
                  <p className="text-sm text-slate-900">{formatDate(selectedDocument.storage_metadata.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Updated</p>
                  <p className="text-sm text-slate-900">{formatDate(documentDetails?.updated_at || new Date().toISOString())}</p>
                </div>
              </div>

              {/* Replication Status */}
              {documentDetails?.replication && (
                <div className="mt-6 pt-6 border-t border-slate-200">
                  <h4 className="text-sm font-semibold text-slate-900 mb-4">Replication Status</h4>
                  
                  {/* File Content Replication */}
                  {documentDetails.replication.file_content && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-700 mb-2">File Content (S3)</p>
                      <div className="space-y-2 ml-2">
                        {documentDetails.replication.file_content.s3_primary && (
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${documentDetails.replication.file_content.s3_primary.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {documentDetails.replication.file_content.s3_primary.success ? '✓' : '✗'} Primary
                            </span>
                            {documentDetails.replication.file_content.s3_primary.bucket && (
                              <span className="text-xs text-slate-600">Bucket: {documentDetails.replication.file_content.s3_primary.bucket}</span>
                            )}
                          </div>
                        )}
                        {documentDetails.replication.file_content.s3_replica && (
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${documentDetails.replication.file_content.s3_replica.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {documentDetails.replication.file_content.s3_replica.success ? '✓' : '✗'} Replica
                            </span>
                            {documentDetails.replication.file_content.s3_replica.bucket && (
                              <span className="text-xs text-slate-600">Bucket: {documentDetails.replication.file_content.s3_replica.bucket}</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Metadata Replication */}
                  {documentDetails.replication.metadata && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-700 mb-2">Metadata (SQLite)</p>
                      <div className="space-y-2 ml-2">
                        {documentDetails.replication.metadata.sqlite_primary && (
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${documentDetails.replication.metadata.sqlite_primary.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {documentDetails.replication.metadata.sqlite_primary.success ? '✓' : '✗'} Primary
                            </span>
                            {documentDetails.replication.metadata.sqlite_primary.file_blob_stored && (
                              <span className="text-xs text-slate-600">Blob: Yes</span>
                            )}
                          </div>
                        )}
                        {documentDetails.replication.metadata.sqlite_replica && (
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${documentDetails.replication.metadata.sqlite_replica.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {documentDetails.replication.metadata.sqlite_replica.success ? '✓' : '✗'} Replica
                            </span>
                            {documentDetails.replication.metadata.sqlite_replica.file_blob_stored && (
                              <span className="text-xs text-slate-600">Blob: Yes</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* App Data */}
              {documentDetails?.app_data && Object.keys(documentDetails.app_data).length > 0 && (
                <details className="mt-6 pt-6 border-t border-slate-200">
                  <summary className="cursor-pointer text-sm font-medium text-slate-700 hover:text-slate-900">
                    View App Data
                  </summary>
                  <pre className="mt-3 p-4 bg-slate-900 text-slate-100 text-xs rounded-lg overflow-x-auto">
                    {JSON.stringify(documentDetails.app_data, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </>
        ) : null}
      </div>
      </div>
  );
}
