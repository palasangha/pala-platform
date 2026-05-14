'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useWebSocket } from '@/hooks/useWebSocket';
import { buildSnippet, extractMeaningfulTerms, normalizeQuestionText } from '@/lib/snippetUtils';

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
  excerpt?: string;
  matched_text?: string;
  matched_path?: string;
  match_reason?: string;
  relevance_score?: number;
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
  passage: string;
  matchedPath: string;
  matchReason?: string;
  relevanceScore: number;
  pinnedSnippet?: boolean;
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
  const lowerName = (doc.original_file || '').toLowerCase();
  if (doc.file_format === 'docx' || lowerName.endsWith('.docx')) {
    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  }
  if (doc.file_format === 'pdf') return 'application/pdf';
  if (doc.file_format === 'json') return 'application/json';
  if (doc.file_format === 'md') return 'text/markdown';
  if (doc.file_format === 'txt') return 'text/plain';
  return '';
}

function getPreviewText(doc: TimelineDocument) {
  if (!doc) return '';
  return (
    doc.matched_text ||
    doc.excerpt ||
    doc.search_text ||
    toText(doc.processed_data?.text) ||
    toText(doc.processed_data?.content) ||
    toText(doc.metadata?.content?.summary) ||
    doc.summary ||
    ''
  );
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
  const isDocx = (doc.file_format || '').toLowerCase() === 'docx' || (doc.original_file || '').toLowerCase().endsWith('.docx') || mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

  if (isDocx) {
    const extractedText = toText(doc.processed_data?.result?.content || doc.processed_data?.content || doc.processed_data?.text || summary);
    return (
      <pre className="whitespace-pre-wrap break-words bg-slate-950 border border-slate-700 rounded p-4 text-sm text-slate-200 max-h-[24rem] overflow-auto">
        {extractedText || summary || 'No DOCX text preview available.'}
      </pre>
    );
  }

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

function escapeHtml(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlightText(text: string, query: string) {
  if (!query) return escapeHtml(text);
  const escapedTerms = extractMeaningfulTerms(query)
    .map((term) => term.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'));

  if (escapedTerms.length === 0) return escapeHtml(text);

  const re = new RegExp(escapedTerms.join('|'), 'gi');
  return escapeHtml(text).replace(re, (match) => `<mark class="rounded bg-blue-400/30 text-blue-100 px-1">${match}</mark>`);
}

function getQuestionSnippet(question: any) {
  const evidence = Array.isArray(question?.evidence) ? question.evidence : [];
  return toText(question?.answer_preview).trim() || toText(evidence[0]?.snippet).trim() || '';
}

function dedupeQuestions(questions: any[]) {
  const seen = new Set<string>();
  const out: any[] = [];
  for (const q of questions || []) {
    const key = toText(q?.question_id) || normalizeQuestionText(toText(q?.text || ''));
    if (!seen.has(key)) {
      seen.add(key);
      out.push(q);
    }
  }
  return out;
}

function getQuestionSourceDocumentId(question: any) {
  return toText(question?._sourceDocumentId || question?.document_id || question?.provenance || question?.source_document_id);
}

function getQuestionKey(question: any) {
  return toText(question?.question_id) || normalizeQuestionText(toText(question?.text || ''));
}

function buildExploreNextQuestionLists(queryResults: TimelineDocument[], questionByDocumentId: Record<string, any[]>, activeQuery: string) {
  const grouped = queryResults
    .filter((doc) => Boolean(doc.document_id))
    .map((doc) => ({
      doc,
      questions: (questionByDocumentId[doc.document_id] || []).filter((question) => {
        const text = toText(question?.text).trim();
        if (!text) return false;
        return normalizeQuestionText(text) !== activeQuery;
      }),
    }))
    .filter((entry) => entry.questions.length > 0);

  const seen = new Set<string>();
  const initial: any[] = [];
  const remaining: any[] = [];

  const pushUnique = (target: any[], question: any, doc: TimelineDocument) => {
    const key = getQuestionKey(question);
    if (!key || seen.has(key)) return;
    seen.add(key);
    target.push({
      ...question,
      _sourceDocumentId: doc.document_id,
      _sourceTitle: doc.original_file || doc.title || doc.document_id,
      _sourceRelevance: doc.relevance_score,
    });
  };

  const firstDoc = grouped[0];
  const secondDoc = grouped[1];

  if (firstDoc) {
    for (const question of firstDoc.questions.slice(0, 3)) {
      pushUnique(initial, question, firstDoc.doc);
    }
  }

  if (secondDoc) {
    for (const question of secondDoc.questions.slice(0, 2)) {
      pushUnique(initial, question, secondDoc.doc);
    }
  }

  for (const entry of grouped.slice(2)) {
    for (const question of entry.questions) {
      pushUnique(remaining, question, entry.doc);
    }
  }

  return { initial, remaining };
}

function buildExpandedTimelineQuery(query: string, filter: TimelineFilter, year: string, item?: TimelineItem | null) {
  const parts: string[] = [];
  const trimmed = query.trim();
  const terms = extractMeaningfulTerms(trimmed);
  if (trimmed) parts.push(trimmed);
  if (terms.length > 0) parts.push(terms.join(' '));

  if (filter !== 'all') parts.push(`filter:${filter}`);
  if (year !== 'all') parts.push(`year:${year}`);

  const lower = trimmed.toLowerCase();
  const intentHints: string[] = [];
  if (/\bwhen\b|\bdate\b|\byear\b/.test(lower)) intentHints.push('date', 'dated', 'time');
  if (/\bwhere\b|\bbodhgaya\b|\blocation\b/.test(lower)) intentHints.push('bodhgaya', 'location', 'place');
  if (/\bspoken\b|\bsaid\b|\buttered\b|\btaught\b|\bdiscourse\b/.test(lower)) intentHints.push('spoken', 'said', 'discourse', 'teaching');
  if (/\bpeople\b|\bwho\b/.test(lower)) intentHints.push('speaker', 'author', 'person');

  if (item) {
    const relatedTerms = [...item.people, ...item.places, ...item.topics].filter(Boolean);
    if (relatedTerms.length > 0) parts.push(`related:${relatedTerms.slice(0, 12).join(' OR ')}`);
  }

  if (intentHints.length > 0) parts.push(`intent:${Array.from(new Set(intentHints)).join(' OR ')}`);
  return parts.join(' | ');
}

export function TimelineExplorer() {
  const searchParams = useSearchParams();
  const lastAutoOpenedIdRef = useRef<string | null>(null);
  const { connected, send } = useWebSocket();
  const [documents, setDocuments] = useState<TimelineDocument[]>([]);
  const [queryResults, setQueryResults] = useState<TimelineDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedYear, setSelectedYear] = useState('all');
  const [selectedFilter, setSelectedFilter] = useState<TimelineFilter>('all');
  const [selectedDocument, setSelectedDocument] = useState<TimelineDocument | null>(null);
  const [selectedDetails, setSelectedDetails] = useState<TimelineDocument | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<any[]>([]);
  const [showQuestionDropdown, setShowQuestionDropdown] = useState(false);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [topQuestions, setTopQuestions] = useState<any[]>([]);
  const [topQuestionsMore, setTopQuestionsMore] = useState<any[]>([]);
  const [topQuestionsMoreVisibleCount, setTopQuestionsMoreVisibleCount] = useState(0);
  const [topQuestionsLoading, setTopQuestionsLoading] = useState(false);
  const [pinnedQuestionSourceDocumentId, setPinnedQuestionSourceDocumentId] = useState<string | null>(null);
  const [pinnedQuestionContext, setPinnedQuestionContext] = useState<{ text: string; snippet: string } | null>(null);
  const [showFullFile, setShowFullFile] = useState(false);
  const [openingDocumentId, setOpeningDocumentId] = useState<string | null>(null);

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

  const searchDocuments = useCallback(async (searchText: string) => {
    if (!connected) return;

    const trimmed = searchText.trim();
    if (!trimmed) {
      setQueryResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const expandedQuery = buildExpandedTimelineQuery(trimmed, selectedFilter, selectedYear);
      console.log('[TimelineExplorer] searchDocuments start', { 
        trimmed, 
        expandedQuery, 
        selectedFilter, 
        selectedYear,
        pinnedDocId: pinnedQuestionSourceDocumentId,
      });

      const response: any = await send('tools/invoke', {
        agentId: 'storage-agent',
        name: 'semantic_search_documents',
        arguments: {
          query: expandedQuery,
          limit: 100,
          min_confidence: 0.32,
          include_original_content: true,
        },
      });

      const data = unwrapToolResult(response);
      const docs = Array.isArray(data.documents) ? data.documents : [];
      console.log('[TimelineExplorer] semantic_search_documents returned', { 
        documentCount: docs.length, 
        searchMethod: data.search_method,
        hasPinned: !!pinnedQuestionSourceDocumentId,
      });

      if (docs.length === 0) {
        // When a question is pinned, skip keyword fallback - only use semantic results
        if (pinnedQuestionSourceDocumentId) {
          console.log('[TimelineExplorer] semantic search returned no documents and pinned doc is set; skipping keyword fallback for stricter matching');
          setQueryResults([]);
          return;
        }

        console.log('[TimelineExplorer] semantic search returned no documents; using local keyword fallback');
        const queryTerms = extractMeaningfulTerms(trimmed);
        const fallback = documents.filter((doc) => {
          const searchable = [
            doc.summary,
            doc.document_date,
            doc.original_file,
            doc.type,
            doc.created_by,
            doc.file_format,
            doc.search_text,
            doc.matched_text,
            doc.matched_path,
            doc.metadata ? JSON.stringify(doc.metadata) : '',
            doc.processed_data ? JSON.stringify(doc.processed_data) : '',
            doc.people?.join(' '),
            doc.places?.join(' '),
            doc.topics?.join(' '),
          ].join(' ').toLowerCase();
          return queryTerms.length === 0 || queryTerms.some((term) => searchable.includes(term));
        });
        setQueryResults(fallback.map((doc) => normalizeTimelineDocument(doc)));
        return;
      }

      const mapped = docs
        .map((doc: any) => {
          const matchedText = toText(doc.matched_text);
          const excerptText = toText(doc.excerpt);
          const summaryText = toText(doc.summary);
          const snippetSource = matchedText || excerptText || summaryText;

          console.log('[TimelineExplorer] search result payload', {
            document_id: doc.document_id || doc.id,
            matched_text_len: matchedText.length,
            excerpt_len: excerptText.length,
            summary_len: summaryText.length,
            matched_path: doc.matched_path || doc.match_method,
            snippet_source: matchedText ? 'matched_text' : excerptText ? 'excerpt' : summaryText ? 'summary' : 'none',
          });

          const source: TimelineDocument = normalizeTimelineDocument({
            document_id: toText(doc.document_id || doc.id),
            original_file: toText(doc.filename || doc.original_file),
            type: toText(doc.type),
            file_format: toText(doc.file_format),
            created_at: toText(doc.created_at),
            summary: snippetSource,
            people: Array.isArray(doc.people) ? doc.people : extractNames(doc.people),
            places: Array.isArray(doc.places) ? doc.places : extractNames(doc.places),
            topics: Array.isArray(doc.topics) ? doc.topics : extractNames(doc.topics),
            metadata: doc.metadata,
            processed_data: doc.processed_data,
            app_data: doc.app_data,
            original_file_data: doc.original_file_data,
            original_file_mime: doc.original_file_mime,
            matched_text: matchedText,
            excerpt: excerptText,
            matched_path: toText(doc.matched_path || doc.match_method),
            match_reason: toText(doc.match_reason || doc.matchReason),
            relevance_score: typeof doc.relevance_score === 'number' ? doc.relevance_score : Number(doc.relevance_score || 0),
          });

          if (!source.document_id) return null;

          const fullContentSource =
            toText(source.processed_data?.result?.content) ||
            toText(source.processed_data?.content) ||
            toText(source.processed_data?.text) ||
            toText(source.metadata?.content?.summary?.text) ||
            toText(source.metadata?.content?.summary) ||
            '';

          const anchor = source.matched_text || source.excerpt || '';
          const passage =
            buildSnippet(
              [anchor, fullContentSource, source.summary],
              trimmed,
              anchor,
              6,
            ) ||
            // Fallback: if buildSnippet returns empty, still return the anchor with proper cleanup
            (anchor ? anchor : toText(fullContentSource || source.summary).slice(0, 500));
          
          if (typeof window !== 'undefined' && window.__DEBUG_SNIPPET && (!passage || passage.split('\n').length < 4)) {
            console.log('[TimelineExplorer snippet]', {
              file: source.original_file,
              anchor: anchor?.slice(0, 100),
              fullContentSourceLength: fullContentSource.length,
              summaryLength: (source.summary || '').length,
              passageLines: passage.split('\n').length,
              passage: passage.slice(0, 150),
            });
          }

          return {
            ...source,
            summary: passage,
          };
        })
        .filter(Boolean) as TimelineDocument[];

      setQueryResults(mapped);
    } catch (err) {
      console.log('[TimelineExplorer] searchDocuments error', { error: err instanceof Error ? err.message : String(err) });
      setQueryResults([]);
    } finally {
      setLoading(false);
    }
  }, [connected, send, selectedFilter, selectedYear, documents]);

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

  const visibleDocuments = useMemo(() => {
    if (query.trim()) return queryResults;
    return documents;
  }, [documents, query, queryResults]);

  const visibleExploreNextQuestions = useMemo(() => {
    return [
      ...topQuestions,
      ...topQuestionsMore.slice(0, topQuestionsMoreVisibleCount),
    ];
  }, [topQuestions, topQuestionsMore, topQuestionsMoreVisibleCount]);

  useEffect(() => {
    if (connected) {
      void loadDocuments();
    }
  }, [connected, loadDocuments]);

  useEffect(() => {
    const t = setTimeout(() => {
      if (!query.trim()) {
        setQueryResults([]);
        return;
      }
      void searchDocuments(query);
    }, 300);

    return () => clearTimeout(t);
  }, [query, searchDocuments]);

  useEffect(() => {
    let cancelled = false;

    const loadTopQuestions = async () => {
      if (!connected || !query.trim() || queryResults.length === 0) {
        setTopQuestions([]);
        setTopQuestionsMore([]);
        setTopQuestionsMoreVisibleCount(0);
        return;
      }

      setTopQuestionsLoading(true);
      try {
        const activeQuery = normalizeQuestionText(query);
        const questionByDocumentId: Record<string, any[]> = {};

        for (const doc of queryResults.slice(0, 10)) {
          if (!doc.document_id) continue;

          const response: any = await send('tools/invoke', {
            agentId: 'storage-agent',
            name: 'get_document_questions',
            arguments: { document_id: doc.document_id },
          });

          const data = unwrapToolResult(response);
          const questions = Array.isArray(data?.questions) ? data.questions : [];
          questionByDocumentId[doc.document_id] = dedupeQuestions(questions);
        }

        const { initial, remaining } = buildExploreNextQuestionLists(queryResults.slice(0, 10), questionByDocumentId, activeQuery);

        if (!cancelled) {
          setTopQuestions(initial.slice(0, 5));
          setTopQuestionsMore(remaining);
          setTopQuestionsMoreVisibleCount(0);
        }
      } catch (err) {
        console.error('[TimelineExplorer] Failed to load top questions:', err);
        if (!cancelled) {
          setTopQuestions([]);
          setTopQuestionsMore([]);
          setTopQuestionsMoreVisibleCount(0);
        }
      } finally {
        if (!cancelled) {
          setTopQuestionsLoading(false);
        }
      }
    };

    void loadTopQuestions();

    return () => {
      cancelled = true;
    };
  }, [connected, query, queryResults, send]);

  const timelineItems = useMemo<TimelineItem[]>(() => {
    return visibleDocuments
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
        const fullContentSource =
          toText(normalized.processed_data?.result?.content) ||
          toText(normalized.processed_data?.content) ||
          toText(normalized.processed_data?.text) ||
          toText(normalized.metadata?.content?.summary?.text) ||
          toText(normalized.metadata?.content?.summary) ||
          '';
        const documentId = toText(doc.document_id || doc.id);
        const isPinnedQuestionMatch =
          pinnedQuestionSourceDocumentId &&
          pinnedQuestionContext &&
          documentId === pinnedQuestionSourceDocumentId &&
          normalizeQuestionText(query) === normalizeQuestionText(pinnedQuestionContext.text);
        const anchor = isPinnedQuestionMatch
          ? (pinnedQuestionContext?.snippet || normalized.matched_text || normalized.excerpt || '')
          : (normalized.matched_text || normalized.excerpt || '');
        const passageSource = fullContentSource || normalized.summary || normalized.search_text || summary;

        const pinnedSnippetContext = isPinnedQuestionMatch
          ? pinnedQuestionContext?.snippet || ''
          : '';
        const defaultContext = buildSnippet(
          [anchor, fullContentSource, normalized.summary, normalized.search_text || ''],
          query,
          anchor,
          999,
        );

        const passage =
          pinnedSnippetContext ||
          defaultContext ||
          toText(anchor || passageSource).slice(0, 500) ||
          summary;

        return {
          documentId,
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
          passage,
          pinnedSnippet: isPinnedQuestionMatch,
          matchedPath: toText(doc.matched_path || doc.match_method),
          matchReason: toText(doc.match_reason || doc.matchReason),
          relevanceScore: Number(doc.relevance_score || 0),
        };
      })
      .filter((item) => item.documentId);
  }, [pinnedQuestionContext, pinnedQuestionSourceDocumentId, query, visibleDocuments]);

  const filteredItems = useMemo(() => {
    return timelineItems
      .filter((item) => {
        if (selectedYear !== 'all' && item.year !== selectedYear) return false;
        if (selectedFilter === 'dated' && item.dateLabel === 'Unknown date') return false;
        if (selectedFilter === 'people' && item.people.length === 0) return false;
        if (selectedFilter === 'places' && item.places.length === 0) return false;
        if (selectedFilter === 'topics' && item.topics.length === 0) return false;

        return true;
      })
      .sort((a, b) => {
        if (pinnedQuestionSourceDocumentId) {
          if (a.documentId === pinnedQuestionSourceDocumentId && b.documentId !== pinnedQuestionSourceDocumentId) return -1;
          if (b.documentId === pinnedQuestionSourceDocumentId && a.documentId !== pinnedQuestionSourceDocumentId) return 1;
        }

        if (query.trim()) {
          return (b.relevanceScore - a.relevanceScore) || a.sortDate.localeCompare(b.sortDate);
        }
        return a.sortDate.localeCompare(b.sortDate);
      });
  }, [pinnedQuestionSourceDocumentId, query, selectedFilter, selectedYear, timelineItems]);

  useEffect(() => {
    log('search/filter changed', { query, selectedYear, selectedFilter });
  }, [log, query, selectedFilter, selectedYear]);

  useEffect(() => {
    log('filtered items updated', { total: timelineItems.length, filtered: filteredItems.length });
  }, [filteredItems.length, log, timelineItems.length]);

  const selectedTimelineItem = useMemo(() => {
    if (!selectedDocument && filteredItems.length > 0) return filteredItems[0];
    return (
      filteredItems.find((item) => item.documentId === selectedDocument?.document_id) ||
      documents.find((item) => item.document_id === selectedDocument?.document_id) ||
      null
    );
  }, [documents, filteredItems, selectedDocument]);

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
    setShowFullFile(false);
    void loadDocumentDetails(item.documentId);
  }, [loadDocumentDetails]);

  const openFullFile = useCallback(() => {
    if (!selectedTimelineItem) return;
    setShowFullFile(true);
    setShowRawJson(false);
    if (!selectedDetails || selectedDetails.document_id !== selectedTimelineItem.documentId) {
      void loadDocumentDetails(selectedTimelineItem.documentId);
    }
  }, [loadDocumentDetails, selectedDetails, selectedTimelineItem]);

  const openDocumentInViewer = useCallback(
    (documentId: string) => {
      if (!documentId) return;
      const item = filteredItems.find((i) => i.documentId === documentId);
      if (item) {
        setSelectedDocument({ document_id: documentId, ...item.source });
      } else {
        setSelectedDocument({ document_id: documentId });
      }
      setSelectedDetails(null);
      setShowRawJson(false);
      setShowFullFile(true);
      void loadDocumentDetails(documentId);
    },
    [filteredItems, loadDocumentDetails]
  );

  const openFileInNewWindow = useCallback(
    (documentId: string) => {
      openDocumentInViewer(documentId);
    },
    [openDocumentInViewer]
  );

  useEffect(() => {
    const docId = searchParams.get('open');
    if (!docId) return;
    if (lastAutoOpenedIdRef.current === docId) return;
    lastAutoOpenedIdRef.current = docId;
    openDocumentInViewer(docId);
  }, [openDocumentInViewer, searchParams]);

  useEffect(() => {
    if (filteredItems.length === 0) return;

    const currentId = selectedDocument?.document_id;
    const stillVisible = currentId ? filteredItems.some((item) => item.documentId === currentId) : false;

    if (!stillVisible) {
      openItem(filteredItems[0]);
    }
  }, [filteredItems, openItem, selectedDocument?.document_id]);

  return (
    <div className="min-h-screen bg-black text-slate-100">
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="space-y-4">
          {/* Search Bar Section */}
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={query}
              onChange={(e) => {
                const newQuery = e.target.value;
                setPinnedQuestionSourceDocumentId(null);
                setPinnedQuestionContext(null);
                setQuery(newQuery);
                
                // Auto-load question suggestions when user types
                if (newQuery.trim() && connected && !loadingQuestions) {
                  setLoadingQuestions(true);
                  send('tools/invoke', {
                    agentId: 'storage-agent',
                    name: 'search_questions',
                    arguments: {
                      query: newQuery.trim(),
                      limit: 5,
                      similarity_threshold: 0.3,
                    },
                  }).then((response: any) => {
                    const data = unwrapToolResult(response);
                    if (data?.questions) {
                      const unique = dedupeQuestions(data.questions || []);
                      setSuggestedQuestions(unique.slice(0, 5));
                      setShowQuestionDropdown(true);
                      console.log('[TimelineExplorer] Loaded', unique.length, 'suggested questions (deduped)');
                    } else {
                      setSuggestedQuestions([]);
                    }
                    setLoadingQuestions(false);
                  }).catch((err: any) => {
                    console.error('[TimelineExplorer] Error loading questions:', err);
                    setSuggestedQuestions([]);
                    setLoadingQuestions(false);
                  });
                } else if (!newQuery.trim()) {
                  setSuggestedQuestions([]);
                  setShowQuestionDropdown(false);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  setShowQuestionDropdown(false);
                  setPinnedQuestionSourceDocumentId(null);
                  setPinnedQuestionContext(null);
                  const value = (e.target as HTMLInputElement).value || query;
                  void searchDocuments(value.trim());
                }
              }}
              placeholder="Search titles, summaries, people, places, and metadata..."
              className="w-full rounded-lg bg-slate-950 border border-slate-700 px-4 py-3 pl-10 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {query && (
              <button
                onClick={() => {
                  setQuery('');
                  setQueryResults([]);
                  setPinnedQuestionSourceDocumentId(null);
                  setPinnedQuestionContext(null);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-sm font-medium"
              >
                Clear
              </button>
            )}
            
            {/* Question suggestions dropdown */}
            {showQuestionDropdown && suggestedQuestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-slate-900 border border-slate-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                <div className="p-2">
                  <p className="text-xs text-slate-400 px-2 py-1">Similar pre-generated questions:</p>
                  {suggestedQuestions.map((q: any, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => {
                        // Keep the selected question as the search input and pin its source document first.
                        const sourceDocumentId = q.document_id || q.provenance || q.source_document_id;
                        if (sourceDocumentId) {
                          console.log('[TimelineExplorer] Pinning provenance document for selected question:', {
                            question: q.text,
                            sourceDocumentId,
                            similarity: q.similarity,
                          });
                          setPinnedQuestionSourceDocumentId(sourceDocumentId);
                          setPinnedQuestionContext({
                            text: q.text,
                            snippet: getQuestionSnippet(q),
                          });
                        } else {
                          console.log('[TimelineExplorer] No source document id on selected question; leaving current view unchanged', q);
                          setPinnedQuestionSourceDocumentId(null);
                          setPinnedQuestionContext(null);
                        }
                        setShowQuestionDropdown(false);
                        setQuery(q.text);
                      }}
                      className="w-full text-left px-2 py-2 hover:bg-slate-800 rounded text-sm text-slate-200 transition"
                    >
                      <div className="font-medium truncate">{q.text}</div>
                      <div className="text-xs text-slate-400">
                        Similarity: {(q.similarity * 100).toFixed(0)}%
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {loadingQuestions && <p className="mt-2 text-xs text-slate-400">Loading question suggestions...</p>}
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-800">
            <button
              type="button"
              onClick={() => setSelectedFilter('dated')}
              className={`px-3 py-2 text-sm transition flex items-center gap-2 ${selectedFilter === 'dated' ? 'text-slate-100 border-b-2 border-blue-500' : 'text-slate-300 hover:text-slate-100'}`}
            >
              📅 Date
            </button>
            <button
              type="button"
              onClick={() => setSelectedFilter('topics')}
              className={`px-3 py-2 text-sm transition flex items-center gap-2 ${selectedFilter === 'topics' ? 'text-slate-100 border-b-2 border-blue-500' : 'text-slate-300 hover:text-slate-100'}`}
            >
              🏷️ Tags
            </button>
            <button
              type="button"
              onClick={() => setSelectedFilter('people')}
              className={`px-3 py-2 text-sm transition flex items-center gap-2 ${selectedFilter === 'people' ? 'text-slate-100 border-b-2 border-blue-500' : 'text-slate-300 hover:text-slate-100'}`}
            >
              👤 Entities
            </button>
            <button
              type="button"
              onClick={() => setSelectedFilter('all')}
              className={`ml-auto px-3 py-2 text-sm transition flex items-center gap-2 ${selectedFilter === 'all' ? 'text-slate-100 border-b-2 border-blue-500' : 'text-slate-300 hover:text-slate-100'}`}
            >
              All
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_20rem] gap-8 items-start">
            {/* Results Section */}
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-400">{filteredItems.length} results</p>
                {loading && <p className="text-xs text-slate-400">Loading...</p>}
              </div>

              {error && (
                <div className="rounded-lg border border-red-700 bg-red-950 p-4 text-sm text-red-200">
                  {error}
                </div>
              )}

              {!loading && filteredItems.length === 0 && (
                <div className="rounded-lg border border-slate-800 bg-slate-800/50 p-10 text-center text-slate-400">
                  No documents match your search.
                </div>
              )}

              <div className="space-y-4">
                {filteredItems.map((item) => (
                  <div
                    key={item.documentId}
                    role="button"
                    tabIndex={0}
                    onClick={() => openItem(item)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        openItem(item);
                      }
                    }}
                    className="cursor-pointer space-y-2 pb-4 border-b border-slate-800 last:border-b-0 last:pb-0 hover:opacity-80 transition"
                  >
                    {/* File name and relevance score */}
                    <div className="flex items-start justify-between gap-4">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void openFileInNewWindow(item.documentId);
                        }}
                        className="text-base font-medium text-blue-400 hover:text-blue-300 truncate text-left"
                      >
                        📄 {item.title}
                      </button>
                      {typeof item.relevanceScore === 'number' && (
                        <div className="shrink-0 flex items-center gap-2">
                          <div className="flex gap-1">
                            {[...Array(5)].map((_, i) => (
                              <div
                                key={i}
                                className={`w-2 h-2 rounded-full ${
                                  i < Math.round(item.relevanceScore * 5)
                                    ? 'bg-slate-400'
                                    : 'bg-slate-700'
                                }`}
                              />
                            ))}
                          </div>
                          <span className="text-sm text-slate-400 whitespace-nowrap">
                            {Math.round(Math.max(0, Math.min(1, item.relevanceScore)) * 100)}%
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Snippet text */}
                    {(item.passage || item.summary) && (
                      <p
                        className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap"
                        dangerouslySetInnerHTML={{ __html: highlightText(item.passage || item.summary, query) }}
                      />
                    )}

                    {/* Metadata footer */}
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      {item.createdBy === 'ocr-agent' && <span>✓ OCR</span>}
                      <span>{item.dateLabel}</span>
                      {item.matchReason && <span>•</span>}
                      {item.matchReason && (
                        <span className="text-slate-600">
                          {item.matchReason}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Suggested Questions Sidebar */}
            <aside className="sticky top-8 space-y-4">
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
                <h3 className="text-sm font-semibold text-slate-100 mb-4 uppercase tracking-wider">Suggested</h3>

                {!query.trim() ? (
                  <p className="text-xs text-slate-400">Search to load suggestions.</p>
                ) : topQuestionsLoading ? (
                  <p className="text-xs text-slate-400">Loading suggestions...</p>
                ) : visibleExploreNextQuestions.length === 0 ? (
                  <p className="text-xs text-slate-400">No suggestions found.</p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {visibleExploreNextQuestions && visibleExploreNextQuestions.length > 0 ? (
                      <>
                        {visibleExploreNextQuestions.map((question: any, index: number) => {
                          if (!question) return null;
                          return (
                            <button
                              key={question.question_id || `top-question-${index}`}
                              type="button"
                              onClick={() => {
                                const sourceDocumentId = getQuestionSourceDocumentId(question);
                                if (sourceDocumentId) {
                                  setPinnedQuestionSourceDocumentId(sourceDocumentId);
                                  setPinnedQuestionContext({
                                    text: question.text,
                                    snippet: getQuestionSnippet(question),
                                  });
                                }
                                setShowQuestionDropdown(false);
                                setQuery(question.text);
                              }}
                              className="w-full flex items-start gap-3 p-3 text-left hover:bg-slate-800/50 rounded-lg transition group"
                            >
                              <span className="text-slate-500 group-hover:text-slate-400 mt-0.5">→</span>
                              <span className="text-sm text-slate-300 group-hover:text-slate-100">{question.text}</span>
                            </button>
                          );
                        })}
                        {topQuestionsMoreVisibleCount < topQuestionsMore.length && (
                          <button
                            type="button"
                            onClick={() => {
                              setTopQuestionsMoreVisibleCount((current) => Math.min(current + 5, topQuestionsMore.length));
                            }}
                            className="w-full py-3 text-center text-sm font-medium text-slate-400 hover:text-slate-300 transition border-t border-slate-700 mt-2"
                          >
                            {topQuestionsMore.length - topQuestionsMoreVisibleCount} more suggestions ↓
                          </button>
                        )}
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            </aside>
          </div>
        </div>
      </main>

      {showFullFile && selectedTimelineItem && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="flex items-center justify-between gap-4 border-b border-slate-800 px-6 py-4 bg-slate-950">
            <div className="flex-1 min-w-0">
              <p className="text-xs uppercase tracking-wide text-slate-400">Full file view</p>
              <h3 className="text-xl font-semibold text-white break-words">{selectedTimelineItem.title}</h3>
              <p className="text-sm text-slate-400 mt-1">{selectedTimelineItem.dateLabel}</p>
            </div>
            <button
              type="button"
              onClick={() => setShowFullFile(false)}
              className="shrink-0 rounded border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              Close
            </button>
          </div>

          <div className="flex-1 overflow-auto bg-slate-900">
            {detailsLoading && <p className="p-6 text-sm text-slate-400">Loading document details...</p>}
            {selectedDetails ? (
              <div className="p-6 space-y-6">
                <div className="rounded border border-slate-700 bg-slate-950 p-4 text-sm text-slate-300">
                  <p><span className="text-slate-400">File:</span> {selectedDetails.original_file || selectedDetails.document_id}</p>
                  <p><span className="text-slate-400">Type:</span> {selectedDetails.type || 'unknown'}</p>
                  <p><span className="text-slate-400">Created by:</span> {selectedDetails.created_by || 'unknown'}</p>
                  <p><span className="text-slate-400">Format:</span> {selectedDetails.file_format || 'unknown'}</p>
                </div>

                <div className="max-w-4xl">
                  {renderInlinePreview(selectedDetails)}
                </div>

                <div className="rounded border border-slate-700 bg-slate-950 p-4">
                  <button
                    type="button"
                    onClick={() => setShowRawJson((current) => !current)}
                    className="w-full flex items-center justify-between text-sm text-slate-200 font-medium"
                  >
                    <span>Raw JSON</span>
                    <span>{showRawJson ? '▼' : '▶'}</span>
                  </button>
                  {showRawJson && (
                    <pre className="mt-4 max-h-96 overflow-auto text-xs text-slate-300 whitespace-pre-wrap font-mono">
                      {JSON.stringify(selectedDetails, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              !detailsLoading && <p className="p-6 text-sm text-slate-400">No file details available yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default TimelineExplorer;