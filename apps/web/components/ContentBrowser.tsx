'use client';

import { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface StoredContent {
  document_id: string;
  type: string;
  metadata_score?: number;
  missing_metadata_fields?: string[];
  file_hash?: string;
  original_file: string;
  file_format: string;
  file_size?: number;
  created_by: string;
  created_at: string;
  updated_at?: string;
  version: number;
  processed_data?: Record<string, any> | string | null;
  metadata?: Record<string, any>;
  app_data?: Record<string, any>;
  provider_id?: string;
  storage_location?: string;
  signature?: string | null;
  tags?: Record<string, string> | null;
  deleted_at?: string | null;
  // From retrieve_document response
  original_file_data?: string;
  original_file_size?: number;
  original_file_error?: string;
  // From store_document response
  db_storage_location?: string;
  db_provider_id?: string;
  replication?: {
    file_content?: {
      s3_primary?: Record<string, any>;
      s3_replica?: Record<string, any>;
    };
    metadata?: {
      sqlite_primary?: Record<string, any>;
      sqlite_replica?: Record<string, any>;
    };
  };
  s3_result?: Record<string, any>;
  duplicate?: boolean;
  message?: string;
}

interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

interface MetadataFormState {
  summary: string;
  documentDate: string;
  language: string;
  people: string;
  places: string;
  topics: string;
  organizations: string;
}

const EMPTY_METADATA_FORM: MetadataFormState = {
  summary: '',
  documentDate: '',
  language: '',
  people: '',
  places: '',
  topics: '',
  organizations: '',
};

function isPlainObject(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function firstDefined(...values: any[]): any {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return undefined;
}

function toText(value: any): string {
  if (typeof value === 'string') return value.trim();
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return value.map(toText).filter(Boolean).join(', ');
  }
  if (isPlainObject(value)) {
    return toText(firstDefined(value.text, value.value, value.name, value.title));
  }
  return '';
}

function toStringList(value: any): string[] {
  if (Array.isArray(value)) {
    return value
      .flatMap((item) => toStringList(item))
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(/[\n,]/)
      .map((entry) => entry.trim())
      .filter(Boolean);
  }
  if (isPlainObject(value)) {
    const directValue = firstDefined(
      value.name,
      value.title,
      value.label,
      value.value,
      value.text,
      value.location,
      value.place,
      value.city,
      value.state,
      value.country,
    );
    if (directValue !== undefined && directValue !== null && directValue !== '') {
      return toStringList(directValue);
    }
    return toStringList(firstDefined(
      value.items,
      value.values,
      value.names,
      value.locations,
      value.people,
      value.topics,
      value.creator,
      value.contributor,
      value.subject,
      value.summary,
    ));
  }
  return [];
}

function mergeCommaValues(...values: any[]): string {
  const seen = new Set<string>();
  const items: string[] = [];

  values.forEach((value) => {
    toStringList(value).forEach((entry) => {
      const normalized = entry.toLowerCase();
      if (!seen.has(normalized)) {
        seen.add(normalized);
        items.push(entry);
      }
    });
  });

  return items.join(', ');
}

function splitCommaList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function buildMetadataFormState(metadata?: Record<string, any> | null, processedData?: Record<string, any> | string | null): MetadataFormState {
  const metadataObject = isPlainObject(metadata) ? metadata : {};
  const processedObject = isPlainObject(processedData) ? processedData : {};
  const metadataPala = isPlainObject(metadataObject.pala_metadata) ? metadataObject.pala_metadata : {};
  const metadataContent = isPlainObject(metadataObject.content) ? metadataObject.content : {};
  const metadataDocument = isPlainObject(metadataObject.document) ? metadataObject.document : {};
  const processedResult = isPlainObject(processedObject.result) ? processedObject.result : {};
  const processedMetadata = isPlainObject(processedObject.metadata) ? processedObject.metadata : {};
  const processedResultMetadata = isPlainObject(processedResult.metadata) ? processedResult.metadata : {};
  const processedPala = isPlainObject(processedResult.pala_metadata) ? processedResult.pala_metadata : {};
  const processedArchipelago = isPlainObject(processedResult.archipelago_metadata) ? processedResult.archipelago_metadata : {};
  const processedExtractedFields = isPlainObject(processedObject.extracted_fields)
    ? processedObject.extracted_fields
    : isPlainObject(processedResult.extracted_fields)
      ? processedResult.extracted_fields
      : {};

  return {
    summary: toText(firstDefined(
      metadataObject.summary,
      metadataContent.summary,
      metadataPala.content?.summary,
      metadataDocument.summary,
      processedObject.summary,
      processedObject.text,
      processedResult.summary?.text,
      processedPala.content?.summary,
      processedPala.content?.summary?.text,
      processedPala.description,
      processedArchipelago.description,
      processedExtractedFields.summary?.text,
      processedPala.content?.summary?.text,
    )),
    documentDate: toText(firstDefined(
      metadataObject.document_date,
      metadataObject.date,
      metadataDocument.date?.value,
      metadataPala.document?.date?.value,
      metadataPala.document_metadata?.date?.value,
      processedObject.document_date,
      processedObject.date,
      processedResult.document_date,
      processedPala.document?.date?.value,
      processedPala.document_metadata?.date?.value,
      processedArchipelago.date_issued,
      processedArchipelago.date_created,
      processedExtractedFields.document_date?.value,
    )),
    language: toText(firstDefined(
      metadataObject.language,
      metadataContent.language,
      metadataPala.content?.language,
      metadataPala.document_metadata?.language,
      processedObject.language,
      processedResult.language,
      processedPala.document_metadata?.language,
      processedArchipelago.language,
    )),
    people: mergeCommaValues(
      metadataObject.people,
      metadataObject.parties?.people,
      metadataContent.people,
      metadataPala.parties?.people,
      processedObject.people,
      processedResult.people,
      processedPala.parties?.people,
      processedExtractedFields.people,
      processedArchipelago.creator,
      processedArchipelago.contributor,
    ),
    places: mergeCommaValues(
      metadataObject.places,
      metadataObject.locations,
      metadataContent.places,
      metadataPala.places?.locations,
      metadataPala.places,
      processedObject.locations,
      processedMetadata.places,
      processedResult.locations,
      processedResultMetadata.places,
      processedPala.places?.locations,
      processedPala.places,
      processedExtractedFields.locations,
      processedArchipelago.spatial_coverage,
    ),
    topics: mergeCommaValues(
      metadataObject.topics,
      metadataContent.topics,
      metadataPala.content?.topics,
      processedObject.topics,
      processedResult.topics,
      processedPala.content?.topics,
      processedExtractedFields.topics,
      processedArchipelago.subject,
    ),
    organizations: mergeCommaValues(
      metadataObject.organizations,
      metadataObject.parties?.organizations,
      metadataContent.organizations,
      metadataPala.parties?.organizations,
      processedObject.organizations,
      processedResult.organizations,
      processedPala.parties?.organizations,
      processedExtractedFields.organizations,
    ),
  };
}

function buildMetadataPatch(form: MetadataFormState): Record<string, any> {
  const patch: Record<string, any> = {};
  const content: Record<string, any> = {};
  const document: Record<string, any> = {};

  const summary = form.summary.trim();
  const documentDate = form.documentDate.trim();
  const language = form.language.trim();
  const people = splitCommaList(form.people);
  const places = splitCommaList(form.places);
  const topics = splitCommaList(form.topics);
  const organizations = splitCommaList(form.organizations);

  if (summary) {
    patch.summary = summary;
    content.summary = summary;
    document.summary = summary;
  }
  if (documentDate) {
    patch.document_date = documentDate;
    patch.date = documentDate;
    document.date = { value: documentDate };
  }
  if (language) {
    patch.language = language;
    content.language = language;
  }
  if (people.length > 0) {
    patch.people = people;
    patch.parties = { people: people.map((name) => ({ name })) };
    content.people = people;
  }
  if (places.length > 0) {
    patch.places = places;
    patch.locations = places;
    content.places = places;
  }
  if (topics.length > 0) {
    patch.topics = topics;
    content.topics = topics;
  }
  if (organizations.length > 0) {
    patch.organizations = organizations;
    patch.parties = {
      ...(patch.parties || {}),
      organizations: organizations.map((name) => ({ name })),
    };
    content.organizations = organizations;
  }

  if (Object.keys(content).length > 0) {
    patch.content = content;
  }
  if (Object.keys(document).length > 0) {
    patch.document = document;
  }

  return patch;
}

export function ContentBrowser() {
  const { client, connected } = useWebSocket();
  const [contents, setContents] = useState<StoredContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [savingMetadataId, setSavingMetadataId] = useState<string | null>(null);
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
  const [sortBy, setSortBy] = useState<'created_at' | 'metadata_score'>('metadata_score');
  const [selectedContent, setSelectedContent] = useState<StoredContent | null>(
    null
  );
  const [metadataForm, setMetadataForm] = useState<MetadataFormState>(EMPTY_METADATA_FORM);

  const extractToolResult = (response: any): any => {
    const candidates = [
      response?.result?.result?.result,
      response?.result?.result,
      response?.result,
    ];

    for (const candidate of candidates) {
      if (candidate !== undefined && candidate !== null) {
        return candidate;
      }
    }

    return undefined;
  };

  const formatMetadataScore = (score?: number) => {
    const safeScore = typeof score === 'number' ? score : 0;
    return `${safeScore.toFixed(0)}%`;
  };

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
        sort_by: sortBy,
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
      const requestId = request.id;

      console.log('Sending list_documents request:', request);
      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.id !== requestId) {
            return;
          }
          
          const toolResult = extractToolResult(response);
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
  }, [connected, client, pagination.page, pagination.pageSize, filters, sortBy]);

  useEffect(() => {
    fetchContent();
  }, [fetchContent]);

  const viewDocument = useCallback(
    (documentId: string, includeOriginalFile: boolean = false, editMetadata: boolean = false) => {
      if (!client || !connected) return;

      setLoading(true);
      setError(null);

      const requestId = `retrieve-${Date.now()}`;
      const request = {
        jsonrpc: '2.0',
        method: 'tools/invoke',
        params: {
          agentId: 'storage-agent',
          toolName: 'retrieve_document',
          arguments: { 
            document_id: documentId,
            include_original_file: includeOriginalFile
          },
        },
        id: requestId,
      };

      console.log('[ContentBrowser] Calling retrieve_document:', { documentId, includeOriginalFile });
      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.id !== requestId) {
            return;
          }

          if (response.error) {
            setError(response.error.message || 'Failed to retrieve document');
            console.error('[ContentBrowser] Error retrieving document:', response.error);
          } else {
            const fullDoc = extractToolResult(response);
            if (fullDoc?.document_id) {
              console.log('[ContentBrowser] Document retrieved successfully:', fullDoc);
              setSelectedContent(fullDoc as StoredContent);
              if (editMetadata) {
                const normalizedForm = buildMetadataFormState(fullDoc.metadata, fullDoc.processed_data);
                setMetadataForm(normalizedForm);
                console.log('[ContentBrowser] Metadata form initialized:', {
                  documentId,
                  fields: normalizedForm,
                });
              }
            } else {
              setError('Could not find document in response');
              console.error('[ContentBrowser] Document not found in response');
            }
          }
        } catch (e) {
          setError('Failed to parse retrieve response');
          console.error('[ContentBrowser] Failed to parse response:', e);
        } finally {
          setLoading(false);
          client.removeEventListener('message', handleMessage);
        }
      };

      client.addEventListener('message', handleMessage);
    },
    [client, connected]
  );

  const handleMetadataFieldChange = useCallback(
    (fieldName: keyof MetadataFormState, value: string) => {
      setMetadataForm((current) => ({
        ...current,
        [fieldName]: value,
      }));
    },
    []
  );

  const openMetadataEditor = useCallback(
    (doc: StoredContent) => {
      console.log('[ContentBrowser] Opening metadata editor for:', doc.document_id);
      viewDocument(doc.document_id, false, true);
    },
    [viewDocument]
  );

  const downloadOriginalDocument = useCallback(
    (doc: StoredContent) => {
      if (!client || !connected) return;

      console.log('[ContentBrowser] Starting download for document:', doc.document_id);
      setLoading(true);
      setError(null);

      const requestId = `download-${Date.now()}`;
      const request = {
        jsonrpc: '2.0',
        method: 'tools/invoke',
        params: {
          agentId: 'storage-agent',
          toolName: 'retrieve_document',
          arguments: { 
            document_id: doc.document_id,
            include_original_file: true
          },
        },
        id: requestId,
      };

      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.id !== requestId) {
            return;
          }

          if (response.error) {
            setError(response.error.message || 'Failed to download document');
            console.error('[ContentBrowser] Error downloading document:', response.error);
          } else {
            const result = extractToolResult(response);
            if (result?.original_file_data) {
              console.log('[ContentBrowser] Download successful, original_file_data present, size:', result.original_file_size);
              try {
                // Decode base64 string to binary
                const binaryString = atob(result.original_file_data);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                  bytes[i] = binaryString.charCodeAt(i);
                }
                
                // Create blob and download
                const blob = new Blob([bytes], { type: 'application/octet-stream' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = doc.original_file || `document-${doc.document_id}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                console.log('[ContentBrowser] File downloaded successfully:', a.download);
              } catch (decodeError) {
                setError(`Failed to decode file: ${decodeError}`);
                console.error('[ContentBrowser] Base64 decode error:', decodeError);
              }
            } else {
              setError('No file content available for download');
              console.error('[ContentBrowser] No original_file_data in response:', result);
            }
          }
        } catch (e) {
          setError('Failed to parse download response');
          console.error('[ContentBrowser] Failed to parse download response:', e);
        } finally {
          setLoading(false);
          client.removeEventListener('message', handleMessage);
        }
      };

      client.addEventListener('message', handleMessage);
    },
    [client, connected]
  );

  const deleteDocument = useCallback(
    (documentId: string) => {
      if (!client || !connected) return;
      const confirmed = window.confirm(
        `Delete document ${documentId}? This cannot be undone.`
      );
      if (!confirmed) return;

      setDeletingId(documentId);
      setError(null);

      const requestId = `delete-${Date.now()}`;
      const request = {
        jsonrpc: '2.0',
        method: 'tools/invoke',
        params: {
          agentId: 'storage-agent',
          toolName: 'delete_document',
          arguments: { document_id: documentId },
        },
        id: requestId,
      };

      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.id !== requestId) {
            return;
          }

          if (response.error) {
            setError(response.error.message || 'Failed to delete document');
          } else {
            const result = extractToolResult(response);
            if (result?.success) {
              setContents((prev) =>
                prev.filter((content) => content.document_id !== documentId)
              );
              if (selectedContent?.document_id === documentId) {
                setSelectedContent(null);
              }
              fetchContent();
            } else {
              setError(result?.message || 'Delete operation did not succeed');
            }
          }
        } catch (e) {
          setError('Failed to parse delete response');
        } finally {
          setDeletingId(null);
          client.removeEventListener('message', handleMessage);
        }
      };

      client.addEventListener('message', handleMessage);
    },
    [client, connected, fetchContent, selectedContent]
  );

  const saveMetadata = useCallback(() => {
    if (!client || !connected || !selectedContent) return;

    setSavingMetadataId(selectedContent.document_id);
    setError(null);

    const parsedMetadata = buildMetadataPatch(metadataForm);
    if (Object.keys(parsedMetadata).length === 0) {
      setError('Enter at least one metadata field before saving.');
      setSavingMetadataId(null);
      return;
    }

    console.log('[ContentBrowser] Saving metadata patch:', {
      documentId: selectedContent.document_id,
      patchKeys: Object.keys(parsedMetadata),
    });

    const requestId = `update-metadata-${Date.now()}`;
    const request = {
      jsonrpc: '2.0',
      method: 'tools/invoke',
      params: {
        agentId: 'storage-agent',
        toolName: 'update_document_metadata',
        arguments: {
          document_id: selectedContent.document_id,
          metadata: parsedMetadata,
          updated_by: 'web-storage-browser',
          replace: false,
        },
      },
      id: requestId,
    };

    console.log('[ContentBrowser] Saving metadata for document:', selectedContent.document_id);
    client.send(JSON.stringify(request));

    const handleMessage = (event: MessageEvent) => {
      try {
        const response = JSON.parse(event.data);
        if (response.id !== requestId) {
          return;
        }

        if (response.error) {
          setError(response.error.message || 'Failed to update metadata');
          console.error('[ContentBrowser] Error updating metadata:', response.error);
        } else {
          const result = extractToolResult(response);
          if (result?.success) {
            setSelectedContent((current) =>
              current
                ? {
                    ...current,
                    metadata: result.metadata || parsedMetadata,
                    updated_at: result.updated_at || current.updated_at,
                    version: result.version || current.version,
                    metadata_score: result.metadata_score ?? current.metadata_score,
                  }
                : current
            );
            const nextForm = buildMetadataFormState(result.metadata || parsedMetadata, selectedContent.processed_data);
            setMetadataForm(nextForm);
            fetchContent();
            console.log('[ContentBrowser] Metadata updated successfully:', result);
          } else {
            setError(result?.message || 'Metadata update did not succeed');
          }
        }
      } catch (e) {
        setError('Failed to parse metadata update response');
        console.error('[ContentBrowser] Failed to parse metadata update response:', e);
      } finally {
        setSavingMetadataId(null);
        client.removeEventListener('message', handleMessage);
      }
    };

    client.addEventListener('message', handleMessage);
  }, [client, connected, fetchContent, metadataForm, selectedContent]);

  const totalPages = Math.ceil(pagination.total / pagination.pageSize);
  const visibleContents = contents.filter((content) => {
    const query = filters.search.trim().toLowerCase();
    if (!query) return true;
    return [
      content.document_id,
      content.original_file,
      content.created_by,
      content.type,
    ]
      .join(' ')
      .toLowerCase()
      .includes(query);
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Metadata Review
          </h2>
          <p className="text-sm text-slate-600">
            Low-score items first. Edit one document at a time.
          </p>
        </div>
        <div className="text-right">
          <span className="text-sm text-slate-600 block">
            {pagination.total} items
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-slate-700 rounded-lg">
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

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Sort By
          </label>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as typeof sortBy);
              setPagination((p) => ({ ...p, page: 1 }));
            }}
            className="w-full px-3 py-2 border border-slate-600 bg-slate-800 rounded-md text-sm text-slate-100"
          >
            <option value="metadata_score">Metadata score</option>
            <option value="created_at">Created date</option>
          </select>
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
                  Metadata available
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
                  <td colSpan={7} className="px-4 py-6 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin h-5 w-5 text-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : visibleContents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                    No documents found
                  </td>
                </tr>
              ) : (
                visibleContents.map((content) => (
                  <tr
                    key={content.document_id}
                    className="border-b border-slate-600 hover:bg-slate-600"
                  >
                    <td className="px-4 py-2 font-mono text-xs text-slate-400">
                      {content.document_id.substring(0, 12)}...
                    </td>
                    <td className="px-4 py-2 text-slate-100">
                      <span
                        className={`inline-flex items-center px-2 py-1 text-xs rounded-full ${
                          (content.metadata_score || 0) >= 80
                            ? 'bg-emerald-900 text-emerald-200'
                            : (content.metadata_score || 0) >= 50
                              ? 'bg-amber-900 text-amber-200'
                              : 'bg-red-900 text-red-200'
                        }`}
                      >
                        {formatMetadataScore(content.metadata_score)}
                      </span>
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
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => viewDocument(content.document_id)}
                          className="text-blue-400 hover:text-blue-300 text-xs font-medium"
                        >
                          View
                        </button>
                        <button
                          onClick={() => openMetadataEditor(content)}
                          className="text-emerald-400 hover:text-emerald-300 text-xs font-medium"
                        >
                          Update metadata
                        </button>
                        <button
                          onClick={() => deleteDocument(content.document_id)}
                          disabled={deletingId === content.document_id}
                          className="text-red-400 hover:text-red-300 text-xs font-medium disabled:opacity-50"
                        >
                          {deletingId === content.document_id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
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

              <div className="bg-slate-50 p-3 rounded text-sm space-y-2 border border-slate-200">
                <div className="flex items-center justify-between gap-3">
                  <label className="text-xs font-medium text-slate-600">
                    Metadata score
                  </label>
                  <span className="text-xs text-slate-500">
                    {formatMetadataScore(selectedContent.metadata_score)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-blue-600"
                    style={{ width: `${selectedContent.metadata_score || 0}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500">Score is calculated from common metadata fields.</p>
              </div>

              <div className="bg-slate-50 p-3 rounded text-sm space-y-2 border border-slate-200">
                <div className="flex items-center justify-between gap-3">
                  <label className="text-xs font-medium text-slate-600">
                    Edit metadata fields
                  </label>
                  <span className="text-[11px] text-slate-500">
                    Enter values in plain language; lists are comma-separated.
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <label className="space-y-1 md:col-span-2">
                    <span className="block text-xs font-medium text-slate-600">Summary</span>
                    <textarea
                      value={metadataForm.summary}
                      onChange={(e) => handleMetadataFieldChange('summary', e.target.value)}
                      className="w-full min-h-24 px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Short summary or abstract"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="block text-xs font-medium text-slate-600">Document date</span>
                    <input
                      value={metadataForm.documentDate}
                      onChange={(e) => handleMetadataFieldChange('documentDate', e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="YYYY-MM-DD or a readable date"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="block text-xs font-medium text-slate-600">Language</span>
                    <input
                      value={metadataForm.language}
                      onChange={(e) => handleMetadataFieldChange('language', e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="en, hi, bo..."
                    />
                  </label>
                  <label className="space-y-1 md:col-span-2">
                    <span className="block text-xs font-medium text-slate-600">People</span>
                    <textarea
                      value={metadataForm.people}
                      onChange={(e) => handleMetadataFieldChange('people', e.target.value)}
                      className="w-full min-h-20 px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Person 1, Person 2"
                    />
                  </label>
                  <label className="space-y-1 md:col-span-2">
                    <span className="block text-xs font-medium text-slate-600">Places</span>
                    <textarea
                      value={metadataForm.places}
                      onChange={(e) => handleMetadataFieldChange('places', e.target.value)}
                      className="w-full min-h-20 px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Place 1, Place 2"
                    />
                  </label>
                  <label className="space-y-1 md:col-span-2">
                    <span className="block text-xs font-medium text-slate-600">Topics</span>
                    <textarea
                      value={metadataForm.topics}
                      onChange={(e) => handleMetadataFieldChange('topics', e.target.value)}
                      className="w-full min-h-20 px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Topic 1, Topic 2"
                    />
                  </label>
                  <label className="space-y-1 md:col-span-2">
                    <span className="block text-xs font-medium text-slate-600">Organizations</span>
                    <textarea
                      value={metadataForm.organizations}
                      onChange={(e) => handleMetadataFieldChange('organizations', e.target.value)}
                      className="w-full min-h-20 px-3 py-2 text-sm bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Organization 1, Organization 2"
                    />
                  </label>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={saveMetadata}
                    disabled={savingMetadataId === selectedContent.document_id}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {savingMetadataId === selectedContent.document_id ? 'Saving...' : 'Save metadata'}
                  </button>
                  <button
                    onClick={() => setMetadataForm(buildMetadataFormState(selectedContent.metadata, selectedContent.processed_data))}
                    className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-900 hover:bg-slate-50"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {selectedContent.processed_data !== undefined && selectedContent.processed_data !== null && (
                <div className="bg-slate-50 p-3 rounded text-sm space-y-2">
                  <label className="text-xs font-medium text-slate-600">
                    Processed Data (content)
                  </label>
                  <pre className="text-xs text-slate-700 overflow-auto max-h-56 bg-white p-2 rounded border border-slate-200">
                    {typeof selectedContent.processed_data === 'string'
                      ? selectedContent.processed_data
                      : JSON.stringify(selectedContent.processed_data, null, 2)}
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

              {selectedContent.storage_location && (
                <div className="bg-blue-50 p-3 rounded text-sm space-y-2 border border-blue-200">
                  <label className="text-xs font-medium text-blue-700">
                    Storage Information
                  </label>
                  <div className="space-y-1 text-xs text-blue-900">
                    <p><strong>Location:</strong> {selectedContent.storage_location}</p>
                    <p><strong>Provider:</strong> {selectedContent.provider_id || 'unknown'}</p>
                    {selectedContent.file_hash && (
                      <p><strong>File Hash:</strong> <code className="text-blue-700">{selectedContent.file_hash}</code></p>
                    )}
                  </div>
                </div>
              )}

              {selectedContent.replication && (
                <div className="bg-purple-50 p-3 rounded text-sm space-y-2 border border-purple-200">
                  <label className="text-xs font-medium text-purple-700">
                    Replication Status
                  </label>
                  <div className="space-y-2">
                    {selectedContent.replication.file_content && (
                      <div className="bg-white p-2 rounded border border-purple-100">
                        <p className="text-xs font-medium text-purple-900 mb-1">File Content (S3)</p>
                        <div className="space-y-1 text-xs text-purple-800">
                          <p>Primary: {selectedContent.replication.file_content.s3_primary?.success ? '✓' : '✗'}</p>
                          <p>Replica: {selectedContent.replication.file_content.s3_replica?.success ? '✓' : selectedContent.replication.file_content.s3_replica?.reason || '✗'}</p>
                        </div>
                      </div>
                    )}
                    {selectedContent.replication.metadata && (
                      <div className="bg-white p-2 rounded border border-purple-100">
                        <p className="text-xs font-medium text-purple-900 mb-1">Metadata (SQLite)</p>
                        <div className="space-y-1 text-xs text-purple-800">
                          <p>Primary: {selectedContent.replication.metadata.sqlite_primary?.success ? '✓' : '✗'}</p>
                          <p>Replica: {selectedContent.replication.metadata.sqlite_replica?.success ? '✓' : selectedContent.replication.metadata.sqlite_replica?.reason || '✗'}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedContent.message && (
                <div className="bg-green-50 p-3 rounded text-sm border border-green-200">
                  <p className="text-xs font-medium text-green-700">{selectedContent.message}</p>
                </div>
              )}

              <div className="bg-slate-50 p-3 rounded text-sm space-y-2">
                <label className="text-xs font-medium text-slate-600">
                  Full Record JSON
                </label>
                <pre className="text-xs text-slate-700 overflow-auto max-h-64 bg-white p-2 rounded border border-slate-200">
                  {JSON.stringify(selectedContent, null, 2)}
                </pre>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  onClick={() => setSelectedContent(null)}
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-900 hover:bg-slate-50"
                >
                  Close
                </button>
                <button
                  onClick={() => downloadOriginalDocument(selectedContent)}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? 'Downloading...' : 'Download Original'}
                </button>
                <button
                  onClick={() => deleteDocument(selectedContent.document_id)}
                  disabled={deletingId === selectedContent.document_id}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingId === selectedContent.document_id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
