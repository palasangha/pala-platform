"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Browse } from './Browse';

type Doc = any;
type SearchResult = {
  id: string;
  docId: string;
  docTitle: string;
  docDate?: string;
  text: string;
  preview?: string;
  matchedPath?: string;
  matchReason?: string;
  score?: number;
  tags?: string[];
};

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlight(text: string, q: string) {
  if (!q) return escapeHtml(text);
  const re = new RegExp(q.split(/\s+/).map((t) => t.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')).join('|'), 'gi');
  return escapeHtml(text).replace(re, (m) => `<mark class="bg-yellow-300 text-yellow-900 font-semibold rounded px-1">${m}</mark>`);
}

function makePreview(text: string, query: string) {
  const cleanText = (text || '').replace(/\s+/g, ' ').trim();
  if (!cleanText) return 'No preview available';
  const queryText = query.trim().toLowerCase();
  if (!queryText) return cleanText.slice(0, 220) + (cleanText.length > 220 ? '…' : '');
  const index = cleanText.toLowerCase().indexOf(queryText);
  if (index === -1) return cleanText.slice(0, 220) + (cleanText.length > 220 ? '…' : '');
  const start = Math.max(0, index - 80);
  const end = Math.min(cleanText.length, index + queryText.length + 140);
  return `${start > 0 ? '…' : ''}${cleanText.slice(start, end)}${end < cleanText.length ? '…' : ''}`;
}

function sentenceWindow(text: string, query: string) {
  const cleanText = (text || '').replace(/\s+/g, ' ').trim();
  if (!cleanText) return 'No preview available';
  const sentences = cleanText.split(/(?<=[.!?])\s+/);
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const hitIndex = sentences.findIndex((sentence) => {
    const lower = sentence.toLowerCase();
    return terms.some((term) => term.length > 2 && lower.includes(term));
  });
  if (hitIndex === -1) return makePreview(cleanText, query);
  const start = Math.max(0, hitIndex - 1);
  const end = Math.min(sentences.length, hitIndex + 2);
  const snippet = sentences.slice(start, end).join(' ');
  return snippet.length > 260 ? `${snippet.slice(0, 260)}…` : snippet;
}

function buildExpandedQuery(query: string, locations: string[], topics: string[], people: string[]) {
  const parts: string[] = [];
  const trimmed = query.trim();
  if (trimmed) parts.push(trimmed);

  if (locations.length) parts.push(`location: ${locations.join(' OR ')}`);
  if (topics.length) parts.push(`topic: ${topics.join(' OR ')}`);
  if (people.length) parts.push(`people: ${people.join(' OR ')}`);

  const lower = trimmed.toLowerCase();
  const intentHints: string[] = [];
  if (/\bwhen\b|\bdate\b|\byear\b/.test(lower)) intentHints.push('date', 'dated', 'time', 'timestamp');
  if (/\bwhere\b|\blocat/.test(lower)) intentHints.push('place', 'location', 'bodhgaya', 'village', 'city', 'site');
  if (/\bspoken\b|\bsaid\b|\bspoken in\b|\bsaid in\b/.test(lower)) intentHints.push('spoken', 'said', 'taught', 'discourse', 'talk', 'uttered', 'speech');
  if (/\bbodhgaya\b/.test(lower)) intentHints.push('bodhgaya', 'bodh gaya');
  if (/\bwho\b|\bperson\b|\bpeople\b/.test(lower)) intentHints.push('speaker', 'author', 'teacher', 'mentioned');

  if (intentHints.length) parts.push(`intent: ${Array.from(new Set(intentHints)).join(' OR ')}`);
  return parts.join(' | ');
}

function extractSearchTerms(query: string, locations: string[], topics: string[], people: string[]) {
  const terms = new Set<string>();
  const pushTerms = (value: string) => {
    value
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 2)
      .forEach((term) => terms.add(term));
  };

  pushTerms(query);
  locations.forEach(pushTerms);
  topics.forEach(pushTerms);
  people.forEach(pushTerms);
  return Array.from(terms);
}

export default function AdvancedExplore() {
  const { connected, send } = useWebSocket();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [activeTab, setActiveTab] = useState<'passages' | 'documents' | 'timeline' | 'browse'>('passages');
  const [page, setPage] = useState(0);
  const [fullDocOpen, setFullDocOpen] = useState(false);
  const [fullDoc, setFullDoc] = useState<Doc | null>(null);

  const [activeLocations, setActiveLocations] = useState<Set<string>>(new Set());
  const [activeTopics, setActiveTopics] = useState<Set<string>>(new Set());
  const [activePeople, setActivePeople] = useState<Set<string>>(new Set());
  const [availableLocations, setAvailableLocations] = useState<string[]>([]);
  const [availableTopics, setAvailableTopics] = useState<string[]>([]);
  const [availablePeople, setAvailablePeople] = useState<string[]>([]);

  // Load available filters on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!send) return;
      try {
        const res: any = await send('tools/invoke', { name: 'list_documents', arguments: { limit: 500, offset: 0 } });
        if (cancelled) return;
        const docs = res?.documents || [];
        
        const locSet = new Set<string>();
        const topicSet = new Set<string>();
        const peopleSet = new Set<string>();
        docs.forEach((d: any) => {
          (d.places || d.metadata?.places || []).forEach((p: any) => p && locSet.add(String(p)));
          (d.topics || d.metadata?.topics || d.tags || []).forEach((t: any) => t && topicSet.add(String(t)));
          (d.people || d.metadata?.people || []).forEach((p: any) => p && peopleSet.add(String(p.name || p)));
        });
        setAvailableLocations(Array.from(locSet).slice(0, 12));
        setAvailableTopics(Array.from(topicSet).slice(0, 12));
        setAvailablePeople(Array.from(peopleSet).slice(0, 12));
      } catch (err) {
        console.error('Failed to load filters', err);
      }
    })();
    return () => { cancelled = true; };
  }, [send]);

  // Server-side semantic search with better error handling
  const performSearch = useCallback(async (q: string, p: number = 0) => {
    if (!send) return;
    setLoading(true);
    try {
      let res: any;
      const expandedQuery = buildExpandedQuery(q, Array.from(activeLocations), Array.from(activeTopics), Array.from(activePeople));
      
      // Try semantic search first
      try {
        res = await send('tools/invoke', {
          name: 'semantic_search_documents',
          arguments: {
            query: expandedQuery || 'all documents',
            limit: 20,
            offset: p * 20,
            min_confidence: 0.35,
            include_original_content: true,
          },
        });
        console.log('semantic_search_documents result:', res);
      } catch (semanticErr) {
        console.warn('semantic_search_documents not available, using list_documents', semanticErr);
        res = null;
      }

      if (res?.documents && res.documents.length > 0) {
        const mapped = res.documents.map((d: any, idx: number) => ({
          id: `${d.document_id || d.id || d._id || d.original_file || Math.random()}-${idx}`,
          docId: String(d.document_id || d.id || d._id || d.original_file || Math.random()),
          docTitle: d.original_file || d.filename || d.title || d.metadata?.title || 'Untitled',
          docDate: d.created_at || d.metadata?.created_at,
          text: d.excerpt || d.matched_text || d.original_file_data || d.summary || d.processed_data || d.text || '',
          preview: d.excerpt || sentenceWindow(d.matched_text || d.original_file_data || d.summary || d.processed_data || d.text || '', q),
          matchedPath: d.matched_path || d.match_method || d.match_reasons?.join(', '),
          matchReason: d.match_reason || d.matchReason || (d.matched_path ? `Match in ${d.matched_path}` : ''),
          score: d.relevance_score ?? d.score ?? 0,
          tags: d.topics || d.tags || d.places || d.metadata?.tags || [],
        }));
        setResults(mapped);
        if (mapped.length > 0) setSelectedResult(mapped[0]);
      } else {
        console.log('No documents found');
        setResults([]);
      }
    } catch (err) {
      console.error('performSearch error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [send, activeLocations, activeTopics, activePeople]);

  // Load full document
  const loadFullDocument = useCallback(async (docId: string) => {
    if (!send) return;
    try {
      const res: any = await send('tools/invoke', { name: 'retrieve_document', arguments: { document_id: docId, include_original_file: true } });
      setFullDoc(res?.document || res);
      setFullDocOpen(true);
    } catch (err) {
      console.error('retrieve_document failed', err);
    }
  }, [send]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(() => {
      setPage(0);
      void performSearch(query, 0);
    }, 300);
    return () => clearTimeout(t);
  }, [query, performSearch]);

  const toggleSet = (setState: React.Dispatch<React.SetStateAction<Set<string>>>, value: string) => {
    setState((prev) => {
      const copy = new Set(prev);
      if (copy.has(value)) copy.delete(value);
      else copy.add(value);
      return copy;
    });
  };

  const removeFilter = (f: string) => {
    setActiveLocations((s) => { const c = new Set(s); c.delete(f); return c; });
    setActiveTopics((s) => { const c = new Set(s); c.delete(f); return c; });
    setActivePeople((s) => { const c = new Set(s); c.delete(f); return c; });
  };

  const clearFilters = () => {
    setActiveLocations(new Set());
    setActiveTopics(new Set());
    setActivePeople(new Set());
  };

  const allFilters = [...activeLocations, ...activeTopics, ...activePeople];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6">
        {/* Left: Filters */}
        <aside className="col-span-3">
          <div className="sticky top-6 rounded-xl border border-slate-800 bg-slate-900/95 p-5 shadow-2xl shadow-black/20">
            <h3 className="mb-4 text-base font-bold uppercase tracking-wide text-slate-100">Filters</h3>

            <div className="mb-5">
              <input
                type="text"
                placeholder="Search documents..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-xs font-semibold text-slate-400">LOCATION</label>
              <div className="flex flex-wrap gap-2">
                {availableLocations.map((l) => (
                  <button
                    key={l}
                    onClick={() => toggleSet(setActiveLocations, l)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
                      activeLocations.has(l)
                        ? 'border-emerald-400 bg-emerald-500 text-white shadow-sm'
                        : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-emerald-400 hover:text-white'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-xs font-semibold text-slate-400">TOPIC</label>
              <div className="flex flex-wrap gap-2">
                {availableTopics.map((t) => (
                  <button
                    key={t}
                    onClick={() => toggleSet(setActiveTopics, t)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
                      activeTopics.has(t)
                        ? 'border-amber-400 bg-amber-500 text-white shadow-sm'
                        : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-amber-400 hover:text-white'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="mb-2 block text-xs font-semibold text-slate-400">PEOPLE</label>
              <div className="flex flex-wrap gap-2">
                {availablePeople.map((p) => (
                  <button
                    key={p}
                    onClick={() => toggleSet(setActivePeople, p)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${
                      activePeople.has(p)
                        ? 'border-violet-400 bg-violet-500 text-white shadow-sm'
                        : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-violet-400 hover:text-white'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4 border-t border-slate-800 pt-4">
              <div className="mb-2 text-xs font-semibold text-slate-400">Active Filters</div>
              <div className="mb-3 flex flex-wrap gap-2">
                {allFilters.length === 0 ? (
                  <span className="text-xs text-slate-500">None</span>
                ) : (
                  allFilters.map((f) => (
                    <span
                      key={f}
                      className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-200"
                    >
                      {f}
                      <button onClick={() => removeFilter(f)} className="font-bold text-slate-400 hover:text-white">
                        ✕
                      </button>
                    </span>
                  ))
                )}
              </div>
              {allFilters.length > 0 && (
                <button onClick={clearFilters} className="text-xs font-medium text-indigo-400 hover:text-indigo-300">
                  Clear all
                </button>
              )}
            </div>
          </div>
        </aside>

        {/* Center: Results */}
        <section className="col-span-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl shadow-black/20">
            <div className="mb-6">
              <div className="mb-3 text-sm font-semibold text-slate-300">
                {loading ? 'Searching…' : `${results.length} ${activeTab === 'timeline' ? 'timeline items' : activeTab === 'documents' ? 'documents' : activeTab === 'browse' ? 'browse results' : 'passages'}`}
              </div>
              <div className="flex gap-1 border-b border-slate-800">
                {['passages', 'documents', 'timeline', 'browse'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? 'border-b-2 border-indigo-400 text-indigo-300'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {activeTab === 'browse' ? (
              <Browse className="w-full h-[32rem]" send={send} />
            ) : (
            <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-2">
              {loading ? (
                <div className="py-8 text-center text-sm text-slate-400">Loading results…</div>
              ) : results.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-400">No results found.</div>
              ) : (
                results.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => setSelectedResult(r)}
                    className={`cursor-pointer rounded-xl border p-4 transition-all ${
                      selectedResult?.id === r.id
                        ? 'border-indigo-400 bg-slate-800/90 shadow-lg'
                        : 'border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="mb-2 flex items-start justify-between gap-4">
                      <div className="font-semibold text-slate-100">{r.docTitle}</div>
                      <div className="text-xs text-slate-500">{r.docDate || '—'}</div>
                    </div>

                    {activeTab === 'timeline' ? (
                      <>
                        <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                          Passage preview
                        </div>
                        <div className="text-sm leading-relaxed text-slate-300">
                          {r.preview || makePreview(r.text, query)}
                        </div>
                        {r.matchReason && (
                          <div className="mt-2 text-xs uppercase tracking-wide text-slate-500">
                            Why: {r.matchReason}
                          </div>
                        )}
                        {r.matchedPath && (
                          <div className="mt-2 text-xs text-slate-500">Hit: {r.matchedPath}</div>
                        )}
                        {r.tags && r.tags.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1">
                            {r.tags.slice(0, 3).map((tag) => (
                              <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        <div className="mt-4 flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              void loadFullDocument(r.docId);
                            }}
                            className="rounded-lg bg-indigo-500 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-600"
                          >
                            Open full file
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedResult(r);
                            }}
                            className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
                          >
                            Preview
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap text-sm text-slate-300" dangerouslySetInnerHTML={{ __html: highlight(r.preview || r.text, query) }} />
                        {r.matchReason && <div className="mt-2 text-xs uppercase tracking-wide text-slate-500">Why: {r.matchReason}</div>}
                        {r.matchedPath && <div className="mt-2 text-xs text-slate-500">Hit: {r.matchedPath}</div>}
                        {r.tags && r.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {r.tags.slice(0, 2).map((tag) => (
                              <span key={tag} className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
            )}

            {activeTab !== 'browse' && (
            <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-800 pt-4">
              <button
                onClick={() => {
                  setPage(Math.max(0, page - 1));
                  void performSearch(query, Math.max(0, page - 1));
                }}
                disabled={page === 0}
                className="rounded border border-slate-700 px-3 py-1 text-sm text-slate-300 disabled:opacity-40 hover:bg-slate-800"
              >
                ← Previous
              </button>
              <span className="text-xs text-slate-500">Page {page + 1}</span>
              <button
                onClick={() => {
                  setPage(page + 1);
                  void performSearch(query, page + 1);
                }}
                className="rounded border border-slate-700 px-3 py-1 text-sm text-slate-300 hover:bg-slate-800"
              >
                Next →
              </button>
            </div>
            )}
          </div>
        </section>

        {/* Right: Details */}
        <aside className="col-span-3">
          <div className="sticky top-6 min-h-[400px] rounded-xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl shadow-black/20">
            {selectedResult ? (
              <>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Document</div>
                <h2 className="mb-4 text-lg font-bold text-slate-100">{selectedResult.docTitle}</h2>

                {query && (
                  <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
                    <div className="text-xs font-semibold text-amber-300">Matching: {query}</div>
                  </div>
                )}

                <div
                  className="mb-4 max-h-48 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-relaxed text-slate-300"
                    dangerouslySetInnerHTML={{ __html: highlight(selectedResult.preview || selectedResult.text, query) }}
                />
                  {selectedResult.matchReason && (
                    <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Why: {selectedResult.matchReason}</div>
                  )}
                  {selectedResult.matchedPath && (
                    <div className="mb-4 text-xs text-slate-500">Hit path: {selectedResult.matchedPath}</div>
                  )}

                {selectedResult.tags && selectedResult.tags.length > 0 && (
                  <div className="mb-4">
                    <div className="mb-2 text-xs font-semibold text-slate-400">Tags</div>
                    <div className="flex flex-wrap gap-2">
                      {selectedResult.tags.map((tag) => (
                        <span key={tag} className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-6 flex gap-2 border-t border-slate-800 pt-4">
                  <button
                    onClick={() => void loadFullDocument(selectedResult.docId)}
                    className="flex-1 rounded-lg bg-indigo-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-600"
                  >
                    Open full document
                  </button>
                  <button className="rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800">
                    Compare
                  </button>
                </div>
              </>
            ) : (
              <div className="py-20 text-center text-sm text-slate-500">Select a result to view details</div>
            )}
          </div>
        </aside>
      </div>

      {/* Full Document Modal */}
      {fullDocOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
              <h3 className="text-lg font-bold text-slate-100">{fullDoc?.title || fullDoc?.metadata?.title || 'Document'}</h3>
              <button onClick={() => setFullDocOpen(false)} className="text-2xl text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5 text-sm leading-relaxed text-slate-300">
              {fullDoc?.summary || fullDoc?.processed_data || fullDoc?.text || JSON.stringify(fullDoc, null, 2) || 'No content available'}
            </div>
            <div className="flex gap-2 border-t border-slate-800 bg-slate-900 px-6 py-4">
              <button
                onClick={() => setFullDocOpen(false)}
                className="flex-1 rounded-lg bg-slate-700 px-4 py-2 font-semibold text-white hover:bg-slate-600"
              >
                Close
              </button>
              <button className="rounded-lg border border-slate-700 px-4 py-2 font-semibold text-slate-200 hover:bg-slate-800">
                Copy citations
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
