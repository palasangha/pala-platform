'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useWebSocket } from '@/hooks/useWebSocket';

type DocumentHitViewerProps = {
  documentId: string;
  initialQuery?: string;
  initialHit?: string;
};

type RetrievedDocument = {
  document_id?: string;
  original_file?: string;
  file_format?: string;
  created_by?: string;
  created_at?: string;
  type?: string;
  metadata?: any;
  processed_data?: any;
  original_file_data?: string;
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

function escapeHtml(text: string) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function extractDocumentText(doc: RetrievedDocument): string {
  const processedResult = doc?.processed_data?.result || doc?.processed_data || {};
  const candidate =
    toText(processedResult?.content) ||
    toText(processedResult?.text) ||
    toText(processedResult?.ocr_text) ||
    toText(doc?.metadata?.content?.summary?.text) ||
    toText(doc?.metadata?.content?.summary) ||
    toText(doc?.original_file_data) ||
    '';

  return candidate;
}

function escapeForRegex(s: string) {
  return s.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
}

// Highlight the full phrase (case-insensitive). Falls back to whole-line escape if empty.
function highlightText(text: string, query: string) {
  const q = (query || '').trim();
  if (!q) return escapeHtml(text);
  const phrase = escapeForRegex(q);
  try {
    const re = new RegExp(phrase, 'gi');
    return escapeHtml(text).replace(re, (match) => `<mark class="rounded bg-amber-400/30 text-amber-100 px-1">${match}</mark>`);
  } catch (err) {
    return escapeHtml(text);
  }
}

function buildSearchableLines(text: string) {
  return text.split(/\r?\n/);
}

export default function DocumentHitViewer({ documentId, initialQuery = '', initialHit = '' }: DocumentHitViewerProps) {
  const { connected, send } = useWebSocket();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documentData, setDocumentData] = useState<RetrievedDocument | null>(null);
  const [searchText, setSearchText] = useState(initialHit || initialQuery);
  const [activeMatchIndex, setActiveMatchIndex] = useState(0);
  const lineRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    setSearchText(initialHit || initialQuery);
    setActiveMatchIndex(0);
  }, [initialHit, initialQuery, documentId]);

  useEffect(() => {
    if (!connected || !send || !documentId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const response: any = await send('tools/invoke', {
          agentId: 'storage-agent',
          name: 'retrieve_document',
          arguments: {
            document_id: documentId,
            include_original_file: true,
          },
        });

        if (cancelled) return;

        const payload = unwrapToolResult(response);
        const doc = payload?.document_id ? payload : payload?.result || payload || null;
        if (doc?.document_id) {
          setDocumentData(doc as RetrievedDocument);
        } else {
          setDocumentData(null);
          setError('Could not load the selected document.');
        }
      } catch (err) {
        if (!cancelled) {
          setDocumentData(null);
          setError(err instanceof Error ? err.message : 'Failed to load document');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [connected, documentId, send]);

  const documentText = useMemo(() => extractDocumentText(documentData || {}), [documentData]);
  const lines = useMemo(() => buildSearchableLines(documentText || ''), [documentText]);

  const matchIndexes = useMemo(() => {
    const phrase = (searchText || '').trim().toLowerCase();
    if (!phrase) return [] as number[];

    return lines
      .map((line, index) => {
        const lower = (line || '').toLowerCase();
        return lower.includes(phrase) ? index : -1;
      })
      .filter((index) => index >= 0);
  }, [lines, searchText]);

  const activeLineIndex = matchIndexes.length > 0 ? matchIndexes[Math.min(activeMatchIndex, matchIndexes.length - 1)] : -1;

  useEffect(() => {
    if (activeLineIndex < 0) return;
    const el = lineRefs.current[activeLineIndex];
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [activeLineIndex, documentId, searchText]);

  useEffect(() => {
    if (matchIndexes.length === 0) return;
    setActiveMatchIndex((current) => Math.min(current, matchIndexes.length - 1));
  }, [matchIndexes.length]);

  const moveMatch = (delta: number) => {
    if (matchIndexes.length === 0) return;
    setActiveMatchIndex((current) => {
      const next = (current + delta + matchIndexes.length) % matchIndexes.length;
      return next;
    });
  };

  const headerLabel = documentData?.original_file || documentData?.document_id || documentId;

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div className="sticky top-0 z-20 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <button
                type="button"
                onClick={() => router.push('/explore')}
                className="mb-2 text-xs font-medium text-gray-500 hover:text-gray-900"
              >
                ← Back
              </button>
              <h1 className="truncate text-lg font-semibold text-gray-900 sm:text-2xl">{headerLabel}</h1>
              <p className="mt-1 text-xs text-gray-500 break-all">{documentId}</p>
            </div>
            <div className="text-right text-xs text-gray-500">
              {documentData?.type ? <p className="capitalize">{documentData.type}</p> : null}
              {documentData?.created_by ? <p>{documentData.created_by}</p> : null}
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              value={searchText}
              onChange={(event) => {
                setSearchText(event.target.value);
                setActiveMatchIndex(0);
              }}
              placeholder="Search within this document"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => moveMatch(-1)}
                disabled={matchIndexes.length === 0}
                className="rounded-lg border border-gray-300 bg-gray-100 px-3 py-2 text-xs font-medium text-gray-700 disabled:opacity-40"
              >
                Prev
              </button>
              <button
                type="button"
                onClick={() => moveMatch(1)}
                disabled={matchIndexes.length === 0}
                className="rounded-lg border border-gray-300 bg-gray-100 px-3 py-2 text-xs font-medium text-gray-700 disabled:opacity-40"
              >
                Next
              </button>
              <span className="text-xs text-gray-500">
                {matchIndexes.length > 0 ? `${Math.min(activeMatchIndex + 1, matchIndexes.length)} / ${matchIndexes.length} hits` : 'No hits'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 py-4 sm:px-6 sm:py-6">
        {loading ? (
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 text-sm text-gray-700">Loading document…</div>
        ) : error ? (
          <div className="rounded-xl border border-red-800 bg-red-950/60 p-6 text-sm text-red-200">{error}</div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <section className="min-w-0 rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="border-b border-gray-200 px-4 py-3 text-xs text-gray-500 sm:px-6">
                <span className="font-medium text-gray-800">{lines.length}</span> lines ·{' '}
                <span className="font-medium text-gray-800">{matchIndexes.length}</span> matches
              </div>
              <div className="max-h-[calc(100vh-14rem)] overflow-auto px-2 py-3 sm:px-4">
                {lines.length > 0 ? (
                  lines.map((line, index) => {
                    const isActive = index === activeLineIndex;
                    return (
                      <div
                        key={`${documentId}-line-${index}`}
                        ref={(element) => {
                          lineRefs.current[index] = element;
                        }}
                        className={`grid grid-cols-[4rem_minmax(0,1fr)] gap-3 rounded-md px-3 py-1.5 text-sm leading-6 ${
                          isActive ? 'bg-amber-50 ring-1 ring-amber-200' : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="select-none text-right font-mono text-[11px] text-gray-500">
                          {index + 1}
                        </div>
                        <div
                          className="min-w-0 whitespace-pre-wrap break-words text-gray-900"
                          dangerouslySetInnerHTML={{ __html: highlightText(line || ' ', searchText) }}
                        />
                      </div>
                    );
                  })
                ) : (
                  <div className="px-4 py-8 text-sm text-gray-500">No extracted text available for this document.</div>
                )}
              </div>
            </section>

            <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
              <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
                <h2 className="mb-2 text-sm font-semibold text-gray-900">Document Info</h2>
                <div className="space-y-1 text-xs text-gray-500">
                  {documentData?.original_file ? <p><span className="text-gray-700">File:</span> {documentData.original_file}</p> : null}
                  {documentData?.file_format ? <p><span className="text-gray-700">Format:</span> {documentData.file_format}</p> : null}
                  {documentData?.created_by ? <p><span className="text-gray-700">Created by:</span> {documentData.created_by}</p> : null}
                  {documentData?.created_at ? <p><span className="text-gray-700">Created:</span> {new Date(documentData.created_at).toLocaleString()}</p> : null}
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
                <h2 className="mb-2 text-sm font-semibold text-gray-900">Tips</h2>
                <ul className="space-y-2 text-xs text-gray-500">
                  <li>• Use the search box to jump between hits.</li>
                  <li>• The view stays responsive on mobile and can scroll independently.</li>
                  <li>• Search terms are highlighted in the text preview.</li>
                </ul>
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}