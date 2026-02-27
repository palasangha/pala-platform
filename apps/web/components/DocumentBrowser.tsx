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
import { useWebSocket } from '@/hooks/useWebSocket';

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

export default function DocumentBrowser() {
  // WebSocket connection
  const { connected, send } = useWebSocket(process.env.NEXT_PUBLIC_MCP_SERVER_URL || 'ws://localhost:3000');
  
  // State
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
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

  // Load documents
  const loadDocuments = useCallback(async (reset = false) => {
    if (!connected) {
      setError('WebSocket not connected');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const offset = reset ? 0 : (page - 1) * limit;
      const args: any = {
        limit,
        offset,
      };
      
      if (contentTypeFilter) {
        args.content_type = contentTypeFilter;
      }

      if (backendFilter) {
        args.backend = backendFilter;
      }
      
      const result = await send('tools/invoke', {
        name: 'list_documents',
        agentId: 'storage-agent',
        arguments: args
      }) as any;
      
      const data = result || {};
      
      if (reset) {
        setDocuments(data.items || []);
      } else {
        setDocuments(prev => [...prev, ...(data.items || [])]);
      }
      
      setHasMore((data.items || []).length === limit);
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
      
      if (result) {
        setStats(result);
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  // View document
  const viewDocument = async (contentId: string) => {
    if (!connected) {
      setError('WebSocket not connected');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await send('tools/invoke', {
        name: 'retrieve_document',
        agentId: 'storage-agent',
        arguments: { content_id: contentId }
      }) as any;
      
      setSelectedDocument(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to retrieve document';
      setError(message);
    } finally {
      setLoading(false);
    }
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
                if (!searchQuery) return true;
                const title = doc.metadata?.document?.title || '';
                const path = doc.metadata?.original_file_path || '';
                return title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                       path.toLowerCase().includes(searchQuery.toLowerCase());
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
                      {doc.metadata?.document?.title || 'Untitled Document'}
                    </h3>
                    <span className="text-xs text-slate-500 ml-2">{formatSize(doc.size)}</span>
                  </div>
                  
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
                  
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                      {doc.backend}
                    </span>
                    <span className="text-xs text-slate-400">
                      v{doc.version}
                    </span>
                  </div>
                </button>
              ))}
          </div>
          
          {/* Load More */}
          {hasMore && !loading && (
            <div className="p-4">
              <button
                onClick={loadMore}
                className="w-full px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg border border-blue-200"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content - Document Viewer */}
      <div className="flex-1 flex flex-col">
        {!selectedDocument && (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            <div className="text-center">
              <svg className="w-24 h-24 mx-auto mb-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-lg">Select a document to view</p>
            </div>
          </div>
        )}

        {selectedDocument && (
          <>
            {/* Document Header */}
            <div className="bg-white border-b border-slate-200 px-6 py-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-slate-900 mb-2">
                    {selectedDocument.enriched_metadata?.document?.title || 'Untitled Document'}
                  </h2>
                  <div className="flex items-center gap-4 text-sm text-slate-600">
                    {selectedDocument.enriched_metadata?.document?.type && (
                      <span>📄 {selectedDocument.enriched_metadata.document.type}</span>
                    )}
                    {selectedDocument.enriched_metadata?.document?.date?.display && (
                      <span>📅 {selectedDocument.enriched_metadata.document.date.display}</span>
                    )}
                    {selectedDocument.enriched_metadata?.document?.language && (
                      <span>🌐 {selectedDocument.enriched_metadata.document.language}</span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300">
                    Export
                  </button>
                  <button className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300">
                    Download
                  </button>
                  <button
                    onClick={() => setSelectedDocument(null)}
                    className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>

            {/* Document Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-4xl mx-auto space-y-6">
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
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
