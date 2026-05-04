'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

type TimelineFilter = 'all' | 'dated' | 'people' | 'places' | 'topics';

type TimelineDocument = {
  document_id?: string;
  id?: string;
  type?: string;
  original_file?: string;
  file_format?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  version?: number;
  summary?: string;
  people?: string[];
  places?: string[];
  topics?: string[];
  document_date?: string;
  search_text?: string;
  metadata?: any;
  processed_data?: any;
  app_data?: any;
  original_file_data?: string;
  original_file_mime?: string;
};

type TimelineItem = {
  documentId: string;
  title: string;
  dateLabel: string;
  sortDate: string;
  year: string;
  summary: string;
  people: string[];
  places: string[];
  topics: string[];
  documentType: string;
  createdBy: string;
  fileFormat: string;
  source: TimelineDocument;
};

function unwrapToolResult(payload: any) {
  let current = payload;
  let depth = 0;
  while (current && typeof current === 'object' && 'result' in current && depth < 6) {
    const next = current.result;
    if (next === undefined) break;
    current = next;
    depth += 1;
  }
  return current || {};
}

function toText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function formatDateLabel(value: string): string {
  if (!value) return 'Unknown date';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function extractNames(value: any): string[] {
  if (!value) return [];
  const values = Array.isArray(value) ? value : [value];
  const result: string[] = [];

  for (const item of values) {
    if (!item) continue;
    if (typeof item === 'string') {
      if (!result.includes(item)) result.push(item);
      continue;
    }
    if (typeof item === 'object') {
      const name = toText(item.name || item.title || item.label || item.value);
      if (name && !result.includes(name)) {
        result.push(name);
      }
    }
  }

  return result;
}

function normalizeTimelineDocument(doc: TimelineDocument): TimelineDocument {
  const metadata = doc.metadata || {};
  const processed = doc.processed_data || {};
  const processedResult = processed?.result || {};
  const pala = processedResult?.pala_metadata || metadata?.pala_metadata || {};
  const archipelago = processedResult?.archipelago_metadata || metadata?.archipelago_metadata || {};
  const extracted = processedResult?.extracted_fields || {};

  const summary =
    toText(doc.summary) ||
    toText(metadata?.content?.summary?.text) ||
    toText(metadata?.content?.summary) ||
    toText(processedResult?.content?.summary?.text) ||
    toText(processedResult?.content?.summary) ||
    toText(processedResult?.summary?.text) ||
    toText(processedResult?.summary) ||
    toText(archipelago?.description) ||
    toText(archipelago?.title) ||
    toText(processed?.summary) ||
    '';

  const peopleSource =
    Array.isArray(doc.people) && doc.people.length > 0
      ? doc.people
      : metadata?.people || metadata?.pala_metadata?.parties?.people || processedResult?.pala_metadata?.parties?.people || extracted?.people || processed?.people;

  const placesSource =
    Array.isArray(doc.places) && doc.places.length > 0
      ? doc.places
      : metadata?.places ||
        metadata?.locations ||
        metadata?.pala_metadata?.places?.locations ||
        processedResult?.pala_metadata?.places?.locations ||
        archipelago?.spatial_coverage ||
        extracted?.locations ||
        processed?.places ||
        processed?.locations;

  const topicsSource =
    Array.isArray(doc.topics) && doc.topics.length > 0
      ? doc.topics
      : metadata?.content?.keywords ||
        metadata?.topics ||
        metadata?.pala_metadata?.content?.topics?.topics ||
        processedResult?.pala_metadata?.content?.topics?.topics ||
        archipelago?.subject ||
        extracted?.topics ||
        processed?.topics;

  const people = extractNames(peopleSource);
  const places = extractNames(placesSource);
  const topics = extractNames(topicsSource);

  const documentDate =
    toText(doc.document_date) ||
    toText(metadata?.document?.date?.value) ||
    toText(metadata?.date?.value) ||
    toText(metadata?.date) ||
    toText(pala?.document_metadata?.date?.value) ||
    toText(processedResult?.document_date?.value) ||
    toText(processedResult?.document_date) ||
    toText(archipelago?.date_issued) ||
    toText(archipelago?.date_created) ||
    toText(extracted?.document_date?.value) ||
    toText(processed?.date) ||
    toText(doc.created_at);

  const searchableParts = [
    summary,
    documentDate,
    doc.original_file,
    doc.type,
    doc.created_by,
    doc.file_format,
    ...(people || []),
    ...(places || []),
    ...(topics || []),
    toText(archipelago?.title),
    toText(archipelago?.description),
    toText(pala?.content?.summary?.text),
    toText(pala?.document_metadata?.type?.value),
  ]
    .filter(Boolean)
    .join(' ')
    .trim();

  return {
    ...doc,
    summary,
    people,
    places,
    topics,
    document_date: documentDate,
    search_text: searchableParts,
  };
}

function getPreviewMimeType(doc: TimelineDocument) {
  if (!doc) return '';
  if (doc.original_file_mime) return doc.original_file_mime;
  if (doc.file_format === 'pdf') return 'application/pdf';
  if (doc.file_format === 'json') return 'application/json';
  if (doc.file_format === 'md') return 'text/markdown';
  if (doc.file_format === 'txt') return 'text/plain';
  return '';
}

function decodeBase64(base64Value: string) {
  try {
    return atob(base64Value);
  } catch {
    return '';
  }
}

function renderInlinePreview(doc: TimelineDocument) {
  const mimeType = getPreviewMimeType(doc);
  const base64Value = doc.original_file_data;
  const summary = toText(doc.metadata?.content?.summary || doc.processed_data?.summary || doc.processed_data?.text || doc.processed_data?.content);

  if (base64Value && mimeType === 'application/pdf') {
    return (
      <iframe
        title={`Preview ${doc.original_file || doc.document_id || 'document'}`}
        src={`data:application/pdf;base64,${base64Value}`}
        className="w-full h-[24rem] rounded border border-slate-700 bg-slate-950"
      />
    );
  }

  if (base64Value && (mimeType.startsWith('text/') || mimeType === 'application/json' || doc.file_format === 'json')) {
    const textContent = decodeBase64(base64Value);
    return (
      <pre className="whitespace-pre-wrap break-words bg-slate-950 border border-slate-700 rounded p-4 text-sm text-slate-200 max-h-[24rem] overflow-auto">
        {textContent || summary || 'No text preview available.'}
      </pre>
    );
  }

  if (base64Value && (mimeType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes((doc.file_format || '').toLowerCase()))) {
    return (
      <img
        src={`data:${mimeType || 'image/*'};base64,${base64Value}`}
        alt={doc.original_file || doc.document_id || 'document preview'}
        className="max-w-full max-h-[24rem] rounded border border-slate-700 bg-slate-950 object-contain"
      />
    );
  }

  return (
    <div className="rounded border border-slate-700 bg-slate-950 p-4 text-sm text-slate-300">
      {summary ? <p className="whitespace-pre-wrap">{summary}</p> : <p>No inline preview available for this file type.</p>}
    </div>
  );
}

export function TimelineExplorer() {
  const { connected, send } = useWebSocket();
  const [documents, setDocuments] = useState<TimelineDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedFilter, setSelectedFilter] = useState<TimelineFilter>('all');
  const [selectedDocument, setSelectedDocument] = useState<TimelineDocument | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<TimelineDocument | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  console.log('[TimelineExplorer] component rendered', { connected, documentsLength: documents.length });

  const loadDocuments = useCallback(async () => {
    if (!connected) return;

    setLoading(true);
    setError(null);

    try {
      console.log('[TimelineExplorer] loadDocuments start', { connected });
      const response: any = await send('tools/invoke', {
        agentId: 'storage-agent',
        name: 'list_documents',
        arguments: {
          limit: 1000,
          offset: 0,
        },
      });

      console.log('[TimelineExplorer] list_documents response received', { responseKeys: Object.keys(response || {}) });
      const data = unwrapToolResult(response);
      const docs = Array.isArray(data.documents) ? data.documents : Array.isArray(data.items) ? data.items : [];
      console.log('[TimelineExplorer] list_documents returned', { documentCount: docs.length });

      const enrichedDocs = await Promise.all(
        docs.map(async (doc: TimelineDocument) => {
          const documentId = doc.document_id || doc.id;
          if (!documentId) return doc;

          try {
            console.log('[TimelineExplorer] invoking retrieve_document', { documentId });
            const detailResponse: any = await send('tools/invoke', {
              agentId: 'storage-agent',
              name: 'retrieve_document',
              arguments: {
                document_id: documentId,
                include_original_file: false,
              },
            });

            const detailData = unwrapToolResult(detailResponse);
            const detailPayload = detailData?.document_id ? detailData : detailData?.result || detailData || {};
            console.log('[TimelineExplorer] retrieve_document returned', {
              documentId,
              detailKeys: Object.keys(detailPayload || {}),
            });
            if (detailPayload?.document_id) {
              return normalizeTimelineDocument({ ...doc, ...detailPayload });
            }
          } catch (err) {
            console.log('[TimelineExplorer] retrieve_document failed; using shallow document', { documentId, error: err instanceof Error ? err.message : String(err) });
          }

          return normalizeTimelineDocument(doc);
        })
      );

      console.log('[TimelineExplorer] enriched documents ready', { enrichedCount: enrichedDocs.length });
      setDocuments(enrichedDocs);
    } catch (err) {
      console.log('[TimelineExplorer] loadDocuments error', { error: err instanceof Error ? err.message : String(err) });
      setError(err instanceof Error ? err.message : 'Failed to load timeline data');
    } finally {
      setLoading(false);
    }
  }, [connected, send]);

  const loadDocumentDetails = useCallback(async (documentId: string) => {
    if (!documentId) return;

    setDetailsLoading(true);
    setError(null);

    try {
      console.log('[TimelineExplorer] loadDocumentDetails start', { documentId });
      const response: any = await send('tools/invoke', {
        agentId: 'storage-agent',
        name: 'retrieve_document',
        arguments: {
          document_id: documentId,
          include_original_file: true,
        },
      });

      console.log('[TimelineExplorer] invoking retrieve_document for detail panel', { documentId });
      const data = unwrapToolResult(response);
      const payload = data?.document_id ? data : data?.result || data || {};
      if (payload?.document_id) {
        console.log('[TimelineExplorer] detail panel loaded', { documentId, keys: Object.keys(payload || {}) });
        setSelectedDetails(payload);
      } else {
        console.log('[TimelineExplorer] detail panel load failed: no document_id', { documentId, keys: Object.keys(payload || {}) });
        setSelectedDetails(null);
        setError('Could not load the selected document.');
      }
    } catch (err) {
      console.log('[TimelineExplorer] loadDocumentDetails error', { documentId, error: err instanceof Error ? err.message : String(err) });
      setError(err instanceof Error ? err.message : 'Failed to load document details');
    } finally {
      setDetailsLoading(false);
    }
  }, [send]);

  const log = useCallback((message: string, payload?: unknown) => {
    console.debug(`[TimelineExplorer] ${message}`, payload ?? '');
  }, []);

  useEffect(() => {
    if (connected) {
      void loadDocuments();
    }
  }, [connected, loadDocuments]);

  const timelineItems = useMemo<TimelineItem[]>(() => {
    return documents
      .map((doc, idx) => {
        const metadata = doc.metadata || {};
        const processed = doc.processed_data || {};

        if (idx === 0) {
          console.log('[TimelineExplorer] first document structure:', {
            doc_keys: Object.keys(doc),
            people: doc.people,
            places: doc.places,
            topics: doc.topics,
            search_text: doc.search_text ? doc.search_text.substring(0, 200) : 'MISSING',
            metadata_keys: Object.keys(metadata),
            processed_keys: Object.keys(processed),
          });
        }

        const documentDate =
          toText(doc.document_date) ||
          toText(metadata?.document?.date?.value) ||
          toText(metadata?.document?.date?.display) ||
          toText(metadata?.date?.value) ||
          toText(metadata?.date?.display) ||
          toText(metadata?.date) ||
          toText(processed?.date) ||
          toText(doc.created_at);

        const parsedDate = new Date(documentDate);
        const sortDate = Number.isNaN(parsedDate.getTime()) ? toText(doc.created_at) || new Date().toISOString() : parsedDate.toISOString();

        const title =
          toText(metadata?.document?.title) ||
          toText(metadata?.title) ||
          toText(doc.original_file) ||
          toText(doc.document_id) ||
          'Untitled document';

        const normalized = normalizeTimelineDocument(doc);
        const summary = normalized.summary || '';
        const people = normalized.people || [];
        const places = normalized.places || [];
        const topics = normalized.topics || [];

        return {
          documentId: toText(doc.document_id || doc.id),
          title,
          dateLabel: formatDateLabel(documentDate),
          sortDate,
          year: String(new Date(sortDate).getFullYear()),
          summary,
          people,
          places,
          topics,
          documentType: toText(doc.type),
          createdBy: toText(doc.created_by),
          fileFormat: toText(doc.file_format),
          source: normalized,
        };
      })
      .filter((item) => item.documentId);
  }, [documents]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return timelineItems
      .filter((item) => {
        if (selectedYear !== 'all' && item.year !== selectedYear) return false;
        if (selectedFilter === 'dated' && item.dateLabel === 'Unknown date') return false;
        if (selectedFilter === 'people' && item.people.length === 0) return false;
        if (selectedFilter === 'places' && item.places.length === 0) return false;
        if (selectedFilter === 'topics' && item.topics.length === 0) return false;

        if (!normalizedQuery) return true;

        const searchable = [
          item.title,
          item.summary,
          item.documentType,
          item.createdBy,
          item.fileFormat,
          item.year,
          item.people.join(' '),
          item.places.join(' '),
          item.topics.join(' '),
          item.source.search_text,
        ]
          .join(' ')
          .toLowerCase();

        return searchable.includes(normalizedQuery);
      })
      .sort((a, b) => a.sortDate.localeCompare(b.sortDate));
  }, [query, selectedFilter, selectedYear, timelineItems]);

  useEffect(() => {
    log('search/filter changed', { query, selectedYear, selectedFilter });
  }, [log, query, selectedFilter, selectedYear]);

  useEffect(() => {
    log('filtered items updated', { total: timelineItems.length, filtered: filteredItems.length });
  }, [filteredItems.length, log, timelineItems.length]);

  const years = useMemo(() => {
    return Array.from(new Set(timelineItems.map((item) => item.year).filter(Boolean))).sort((a, b) => Number(b) - Number(a));
  }, [timelineItems]);

  const stats = useMemo(() => {
    const dated = timelineItems.filter((item) => item.dateLabel !== 'Unknown date').length;
    const peopleCount = timelineItems.filter((item) => item.people.length > 0).length;
    const placesCount = timelineItems.filter((item) => item.places.length > 0).length;
    return { total: timelineItems.length, dated, peopleCount, placesCount };
  }, [timelineItems]);

  const selectedTimelineItem = useMemo(() => {
    if (!selectedDocument && filteredItems.length > 0) return filteredItems[0];
    return filteredItems.find((item) => item.documentId === selectedDocument?.document_id) || null;
  }, [filteredItems, selectedDocument]);

  const relatedDocuments = useMemo(() => {
    if (!selectedTimelineItem) return [];

    const selectedTerms = new Set([...selectedTimelineItem.people, ...selectedTimelineItem.places, ...selectedTimelineItem.topics].map((term) => term.toLowerCase()));

    return filteredItems
      .filter((item) => item.documentId !== selectedTimelineItem.documentId)
      .map((item) => {
        const terms = [...item.people, ...item.places, ...item.topics].map((term) => term.toLowerCase());
        const overlap = terms.filter((term) => selectedTerms.has(term)).length;
        return { item, overlap };
      })
      .filter(({ overlap }) => overlap > 0)
      .sort((a, b) => b.overlap - a.overlap)
      .slice(0, 4)
      .map(({ item }) => item);
  }, [filteredItems, selectedTimelineItem]);

  const openItem = useCallback((item: TimelineItem) => {
    setSelectedDocument({ document_id: item.documentId, ...item.source });
    setSelectedDetails(null);
    setShowRawJson(false);
    void loadDocumentDetails(item.documentId);
  }, [loadDocumentDetails]);

  useEffect(() => {
    if (filteredItems.length === 0) return;

    const currentId = selectedDocument?.document_id;
    const stillVisible = currentId ? filteredItems.some((item) => item.documentId === currentId) : false;

    if (!stillVisible) {
      openItem(filteredItems[0]);
    }
  }, [filteredItems, openItem, selectedDocument?.document_id]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="bg-slate-950 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Timeline Explorer</h1>
                <p className="text-xs text-slate-400">Browse the archive by date, entity, and theme</p>
              </div>
            </div>
          </div>

          <div className={`px-3 py-1 rounded-full text-sm font-medium ${connected ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'}`}>
            {connected ? '● Connected' : '● Disconnected'}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between gap-3 mb-6">
          <Link href="/" className="text-sm text-blue-300 hover:text-blue-200">
            ← Back to dashboard
          </Link>
          <button
            type="button"
            onClick={() => void loadDocuments()}
            className="px-3 py-2 rounded bg-slate-800 border border-slate-700 text-sm text-slate-200 hover:bg-slate-700"
          >
            Refresh archive
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[19rem_minmax(0,1fr)_24rem] gap-6 items-start">
          <aside className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-800 p-4">
              <label className="block text-sm font-medium text-slate-200 mb-2">Search</label>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search titles, summaries, people..."
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-800 p-4 space-y-4">
              <div>
                <p className="text-sm font-medium text-slate-200 mb-2">Filter</p>
                <div className="flex flex-wrap gap-2">
                  {(['all', 'dated', 'people', 'places', 'topics'] as TimelineFilter[]).map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setSelectedFilter(filter)}
                      className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
                        selectedFilter === filter
                          ? 'bg-blue-600 text-white border-blue-500'
                          : 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-700'
                      }`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-slate-200 mb-2">Year</p>
                <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
                  <button
                    type="button"
                    onClick={() => setSelectedYear('all')}
                    className={`px-3 py-1.5 rounded-full text-xs border ${selectedYear === 'all' ? 'bg-slate-200 text-slate-900 border-slate-200' : 'bg-slate-900 text-slate-300 border-slate-700'}`}
                  >
                    All
                  </button>
                  {years.map((year) => (
                    <button
                      key={year}
                      type="button"
                      onClick={() => setSelectedYear(year)}
                      className={`px-3 py-1.5 rounded-full text-xs border ${selectedYear === year ? 'bg-slate-200 text-slate-900 border-slate-200' : 'bg-slate-900 text-slate-300 border-slate-700'}`}
                    >
                      {year}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-slate-900 p-3">
                  <p className="text-[11px] text-slate-400">Documents</p>
                  <p className="text-xl font-semibold text-white">{stats.total}</p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3">
                  <p className="text-[11px] text-slate-400">Dated</p>
                  <p className="text-xl font-semibold text-white">{stats.dated}</p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3">
                  <p className="text-[11px] text-slate-400">People</p>
                  <p className="text-xl font-semibold text-white">{stats.peopleCount}</p>
                </div>
                <div className="rounded-lg bg-slate-900 p-3">
                  <p className="text-[11px] text-slate-400">Places</p>
                  <p className="text-xl font-semibold text-white">{stats.placesCount}</p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-800 p-4 text-sm text-slate-300">
              <p className="font-medium text-slate-200 mb-2">How to use</p>
              <ul className="space-y-2 text-sm list-disc pl-5">
                <li>Search by person, place, topic, or title.</li>
                <li>Click a timeline item to inspect the document.</li>
                <li>Use the detail panel to jump to related items.</li>
              </ul>
            </div>
          </aside>

          <section className="space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-800 p-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-white">Archive timeline</h2>
                <p className="text-sm text-slate-400">{filteredItems.length} matching documents</p>
              </div>
              {loading && <p className="text-sm text-slate-400">Loading...</p>}
            </div>

            {error && (
              <div className="rounded-xl border border-red-700 bg-red-950 p-4 text-sm text-red-200">
                {error}
              </div>
            )}

            {!loading && filteredItems.length === 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-800 p-10 text-center text-slate-400">
                No timeline items match your filters.
              </div>
            )}

            <div className="space-y-3">
              {filteredItems.map((item) => {
                const isSelected = item.documentId === selectedTimelineItem?.documentId;

                return (
                  <button
                    key={item.documentId}
                    type="button"
                    onClick={() => openItem(item)}
                    className={`relative w-full text-left rounded-xl border p-4 transition-colors ${
                      isSelected
                        ? 'bg-slate-700 border-blue-500 shadow-lg'
                        : 'bg-slate-800 border-slate-700 hover:bg-slate-700/80'
                    }`}
                  >
                    <div className="flex gap-4">
                      <div className="relative flex flex-col items-center pt-1">
                        <div className={`w-3 h-3 rounded-full ${isSelected ? 'bg-blue-400' : 'bg-slate-500'}`} />
                        <div className="w-px flex-1 bg-slate-700 mt-2" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-900 text-slate-300 border border-slate-700">
                            {item.dateLabel}
                          </span>
                          {item.documentType && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-100 border border-blue-700">
                              {item.documentType}
                            </span>
                          )}
                          {item.fileFormat && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-900 text-slate-300 border border-slate-700">
                              {item.fileFormat}
                            </span>
                          )}
                        </div>

                        <h3 className="text-base font-semibold text-white break-words">{item.title}</h3>

                        {item.summary && <p className="mt-2 text-sm text-slate-300 line-clamp-2">{item.summary}</p>}

                        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                          {item.people.slice(0, 4).map((person) => (
                            <span key={person} className="px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-100 border border-emerald-700">
                              {person}
                            </span>
                          ))}
                          {item.places.slice(0, 4).map((place) => (
                            <span key={place} className="px-2 py-0.5 rounded-full bg-amber-900 text-amber-100 border border-amber-700">
                              {place}
                            </span>
                          ))}
                          {item.topics.slice(0, 4).map((topic) => (
                            <span key={topic} className="px-2 py-0.5 rounded-full bg-indigo-900 text-indigo-100 border border-indigo-700">
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <aside className="space-y-4 lg:sticky lg:top-4">
            {selectedTimelineItem ? (
              <div className="rounded-xl border border-slate-800 bg-slate-800 p-4 space-y-4">
                <div>
                  <p className="text-xs text-slate-400">Selected document</p>
                  <h3 className="text-lg font-semibold text-white break-words">{selectedTimelineItem.title}</h3>
                  <p className="text-sm text-slate-400 mt-1">{selectedTimelineItem.dateLabel}</p>
                </div>

                <div className="flex flex-wrap gap-2 text-[11px]">
                  {selectedTimelineItem.people.map((person) => (
                    <span key={person} className="px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-100 border border-emerald-700">
                      {person}
                    </span>
                  ))}
                  {selectedTimelineItem.places.map((place) => (
                    <span key={place} className="px-2 py-0.5 rounded-full bg-amber-900 text-amber-100 border border-amber-700">
                      {place}
                    </span>
                  ))}
                  {selectedTimelineItem.topics.map((topic) => (
                    <span key={topic} className="px-2 py-0.5 rounded-full bg-indigo-900 text-indigo-100 border border-indigo-700">
                      {topic}
                    </span>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => void loadDocumentDetails(selectedTimelineItem.documentId)}
                  className="w-full px-3 py-2 rounded bg-slate-700 text-slate-100 hover:bg-slate-600 text-sm"
                >
                  Refresh details
                </button>

                {detailsLoading && <p className="text-sm text-slate-400">Loading document details...</p>}

                {selectedDetails && (
                  <div className="space-y-4">
                    <div className="rounded border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
                      <p><span className="text-slate-500">File:</span> {selectedDetails.original_file || selectedDetails.document_id}</p>
                      <p><span className="text-slate-500">Type:</span> {selectedDetails.type || 'unknown'}</p>
                      <p><span className="text-slate-500">Created by:</span> {selectedDetails.created_by || 'unknown'}</p>
                      <p><span className="text-slate-500">Format:</span> {selectedDetails.file_format || 'unknown'}</p>
                    </div>

                    {renderInlinePreview(selectedDetails)}

                    <div className="rounded border border-slate-700 bg-slate-900 p-3">
                      <button
                        type="button"
                        onClick={() => setShowRawJson((current) => !current)}
                        className="w-full flex items-center justify-between text-sm text-slate-200"
                      >
                        <span>Raw JSON</span>
                        <span>{showRawJson ? 'Hide' : 'Show'}</span>
                      </button>
                      {showRawJson && (
                        <pre className="mt-3 max-h-72 overflow-auto text-xs text-slate-300 whitespace-pre-wrap">
                          {JSON.stringify(selectedDetails, null, 2)}
                        </pre>
                      )}
                    </div>

                    {relatedDocuments.length > 0 && (
                      <div className="rounded border border-slate-700 bg-slate-900 p-3">
                        <p className="text-sm font-semibold text-slate-200 mb-3">Related documents</p>
                        <div className="space-y-2">
                          {relatedDocuments.map((item) => (
                            <button
                              key={item.documentId}
                              type="button"
                              onClick={() => openItem(item)}
                              className="w-full text-left rounded border border-slate-700 bg-slate-950 p-2 hover:bg-slate-800"
                            >
                              <p className="text-sm text-slate-100 break-words">{item.title}</p>
                              <p className="text-xs text-slate-400">{item.dateLabel}</p>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-slate-800 p-4 text-sm text-slate-400">
                Click a timeline item to see more detail.
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}

export default TimelineExplorer;