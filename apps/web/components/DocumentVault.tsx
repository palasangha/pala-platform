'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useWebSocket } from '@/hooks/useWebSocket';

type Document = {
  document_id?: string;
  id?: string;
  title?: string;
  summary?: string;
  people?: string[];
  places?: string[];
  topics?: string[];
  document_date?: string;
  file_format?: string;
  created_at?: string;
  metadata?: any;
  processed_data?: any;
  search_text?: string;
  [key: string]: any;
};

interface SearchState {
  query: string;
  selectedTags: Set<string>;
  selectedDocument: Document | null;
  selectedPeople: Set<string>;
  selectedPlaces: Set<string>;
  selectedYears: Set<string>;
}

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

function normalizeDocument(doc: Document): Document {
  const processed = doc.processed_data?.result || {};
  const pala = processed.pala_metadata || doc.metadata?.pala_metadata || {};
  const archipelago = processed.archipelago_metadata || doc.metadata?.archipelago_metadata || {};

  const people = (pala.parties?.people || []).map((p: any) => typeof p === 'string' ? p : p.name || '').filter(Boolean);
  const places = (pala.places?.locations || archipelago.spatial_coverage || []).map((p: any) => typeof p === 'string' ? p : p.name || '').filter(Boolean);
  const topics = Array.isArray(pala.content?.topics) ? pala.content.topics : [];
  const summary = typeof pala.content?.summary === 'object' ? pala.content.summary.text : pala.content?.summary || archipelago.description || '';

  return {
    ...doc,
    title: doc.metadata?.title || archipelago.title || doc.title || 'Untitled',
    summary: toText(summary),
    people,
    places,
    topics,
    document_date: doc.document_date || pala.document_date || archipelago.date_issued,
    file_format: doc.file_format || 'unknown',
  };
}

/**
 * Full-screen modal for viewing document details
 */
function DocumentModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Modal Header */}
        <div className="sticky top-0 bg-slate-800 border-b border-slate-700 p-6 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold text-white mb-2">{doc.title}</h2>
            {doc.document_date && (
              <p className="text-slate-400 text-sm">
                {new Date(doc.document_date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 text-slate-400 hover:text-white transition text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-8">
          {/* Summary */}
          {doc.summary && (
            <div>
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Summary</h3>
              <p className="text-slate-200 leading-relaxed">{doc.summary}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* People */}
            {doc.people && doc.people.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">People</h3>
                <div className="space-y-2">
                  {doc.people.map((p) => (
                    <div key={p} className="px-3 py-2 bg-purple-900/20 text-purple-300 rounded text-sm">
                      {p}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Places */}
            {doc.places && doc.places.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Locations</h3>
                <div className="space-y-2">
                  {doc.places.map((p) => (
                    <div key={p} className="px-3 py-2 bg-orange-900/20 text-orange-300 rounded text-sm">
                      {p}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Topics */}
            {doc.topics && doc.topics.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Topics</h3>
                <div className="space-y-2">
                  {doc.topics.map((t) => (
                    <div key={t} className="px-3 py-2 bg-green-900/20 text-green-300 rounded text-sm">
                      {t}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* File Info */}
          <div className="border-t border-slate-700 pt-6">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">File Information</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-slate-500">Format</p>
                <p className="text-slate-200 font-mono">{doc.file_format}</p>
              </div>
              {doc.created_at && (
                <div>
                  <p className="text-slate-500">Added</p>
                  <p className="text-slate-200">{new Date(doc.created_at).toLocaleDateString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Explore() {
  const { connected, send } = useWebSocket();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState<SearchState>({
    query: '',
    selectedTags: new Set(),
    selectedDocument: null,
    selectedPeople: new Set(),
    selectedPlaces: new Set(),
    selectedYears: new Set(),
  });

  // Load documents on mount
  useEffect(() => {
    if (!connected) return;
    
    const loadDocs = async () => {
      setLoading(true);
      try {
        const response: any = await send('tools/invoke', {
          agentId: 'storage-agent',
          name: 'list_documents',
          arguments: { limit: 1000, offset: 0 },
        });

        const data = unwrapToolResult(response);
        const docs = Array.isArray(data.documents) ? data.documents : [];
        setDocuments(docs.map(normalizeDocument));
      } catch (error) {
        console.error('Failed to load documents:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDocs();
  }, [connected, send]);

  // Filter documents based on search and selected filters
  const filteredDocs = useMemo(() => {
    let filtered = documents;

    if (state.query) {
      const q = state.query.toLowerCase();
      filtered = filtered.filter((doc) => {
        const searchText = `${doc.title} ${doc.summary} ${(Array.isArray(doc.people) ? doc.people : []).join(' ')} ${(Array.isArray(doc.places) ? doc.places : []).join(' ')} ${(Array.isArray(doc.topics) ? doc.topics : []).join(' ')} ${doc.file_format}`.toLowerCase();
        return searchText.includes(q);
      });
    }

    if (state.selectedPeople.size > 0) {
      filtered = filtered.filter((doc) =>
        Array.from(state.selectedPeople).some((p) => (Array.isArray(doc.people) ? doc.people : []).includes(p))
      );
    }

    if (state.selectedPlaces.size > 0) {
      filtered = filtered.filter((doc) =>
        Array.from(state.selectedPlaces).some((p) => (Array.isArray(doc.places) ? doc.places : []).includes(p))
      );
    }

    if (state.selectedYears.size > 0) {
      filtered = filtered.filter((doc) => {
        if (!doc.document_date) return false;
        const year = new Date(doc.document_date).getFullYear().toString();
        return state.selectedYears.has(year);
      });
    }

    if (state.selectedTags.size > 0) {
      filtered = filtered.filter((doc) =>
        Array.from(state.selectedTags).some((t) => (Array.isArray(doc.topics) ? doc.topics : []).includes(t))
      );
    }

    return filtered;
  }, [documents, state.query, state.selectedPeople, state.selectedPlaces, state.selectedYears, state.selectedTags]);

  // Extract all available people for filter
  const allPeople = useMemo(() => {
    const people = new Map<string, number>();
    documents.forEach((doc) => {
      (Array.isArray(doc.people) ? doc.people : []).forEach((p) => {
        people.set(p, (people.get(p) || 0) + 1);
      });
    });
    return Array.from(people.entries()).sort((a, b) => b[1] - a[1]);
  }, [documents]);

  const allPlaces = useMemo(() => {
    const places = new Map<string, number>();
    documents.forEach((doc) => {
      (Array.isArray(doc.places) ? doc.places : []).forEach((p) => {
        places.set(p, (places.get(p) || 0) + 1);
      });
    });
    return Array.from(places.entries()).sort((a, b) => b[1] - a[1]);
  }, [documents]);

  const allYears = useMemo(() => {
    const years = new Map<string, number>();
    documents.forEach((doc) => {
      if (doc.document_date) {
        const year = new Date(doc.document_date).getFullYear().toString();
        years.set(year, (years.get(year) || 0) + 1);
      }
    });
    return Array.from(years.entries()).sort((a, b) => Number(b[0]) - Number(a[0]));
  }, [documents]);

  const allTags = useMemo(() => {
    const tags = new Map<string, number>();
    documents.forEach((doc) => {
      (Array.isArray(doc.topics) ? doc.topics : []).forEach((t) => {
        tags.set(t, (tags.get(t) || 0) + 1);
      });
    });
    return Array.from(tags.entries()).sort((a, b) => b[1] - a[1]);
  }, [documents]);

  const toggleTag = useCallback((tag: string) => {
    setState((prev) => {
      const newTags = new Set(prev.selectedTags);
      if (newTags.has(tag)) {
        newTags.delete(tag);
      } else {
        newTags.add(tag);
      }
      return { ...prev, selectedTags: newTags, query: '' };
    });
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col">
      <div className="border-b border-slate-800 bg-slate-950 px-4 py-3 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <Link href="/" className="text-blue-400 hover:text-blue-300 transition text-sm font-medium">
            ← Back to Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-xs text-slate-400">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      <main className="flex-1 overflow-hidden">
        <div className="flex h-full">
          <aside className="hidden lg:block w-80 border-r border-slate-800 bg-slate-900 overflow-y-auto p-6">
            <div className="space-y-6">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 mb-2">Document discovery</p>
                <h1 className="text-4xl font-bold text-white">Explore</h1>
                <p className="text-slate-400 mt-1">Search and browse documents.</p>
              </div>

              {allPeople.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4">👥 People</h3>
                  <div className="flex flex-wrap gap-2">
                    {allPeople.slice(0, 12).map(([person, count]) => (
                      <button
                        key={person}
                        onClick={() => setState((prev) => {
                          const newPeople = new Set(prev.selectedPeople);
                          newPeople.has(person) ? newPeople.delete(person) : newPeople.add(person);
                          return { ...prev, selectedPeople: newPeople, query: '' };
                        })}
                        className={`px-3 py-1.5 rounded-full text-sm transition ${
                          state.selectedPeople.has(person)
                            ? 'bg-purple-600 text-white'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {person} <span className="text-xs opacity-70">({count})</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {allPlaces.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4">📍 Locations</h3>
                  <div className="flex flex-wrap gap-2">
                    {allPlaces.slice(0, 12).map(([place, count]) => (
                      <button
                        key={place}
                        onClick={() => setState((prev) => {
                          const newPlaces = new Set(prev.selectedPlaces);
                          newPlaces.has(place) ? newPlaces.delete(place) : newPlaces.add(place);
                          return { ...prev, selectedPlaces: newPlaces, query: '' };
                        })}
                        className={`px-3 py-1.5 rounded-full text-sm transition ${
                          state.selectedPlaces.has(place)
                            ? 'bg-orange-600 text-white'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {place} <span className="text-xs opacity-70">({count})</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {allYears.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4">📅 Years</h3>
                  <div className="flex flex-wrap gap-2">
                    {allYears.map(([year, count]) => (
                      <button
                        key={year}
                        onClick={() => setState((prev) => {
                          const newYears = new Set(prev.selectedYears);
                          newYears.has(year) ? newYears.delete(year) : newYears.add(year);
                          return { ...prev, selectedYears: newYears, query: '' };
                        })}
                        className={`px-3 py-1.5 rounded-full text-sm transition ${
                          state.selectedYears.has(year)
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {year} <span className="text-xs opacity-70">({count})</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {allTags.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4">🏷️ Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {allTags.slice(0, 12).map(([tag, count]) => (
                      <button
                        key={tag}
                        onClick={() => toggleTag(tag)}
                        className={`px-3 py-1.5 rounded-full text-sm transition ${
                          state.selectedTags.has(tag)
                            ? 'bg-green-600 text-white'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {tag} <span className="text-xs opacity-70">({count})</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {(state.selectedPeople.size > 0 || state.selectedPlaces.size > 0 || state.selectedYears.size > 0 || state.selectedTags.size > 0) && (
                <button
                  onClick={() => setState((prev) => ({
                    ...prev,
                    selectedPeople: new Set(),
                    selectedPlaces: new Set(),
                    selectedYears: new Set(),
                    selectedTags: new Set(),
                  }))}
                  className="w-full px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition text-sm font-medium"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </aside>

          <section className="flex-1 overflow-y-auto px-4 py-8">
            <div className="max-w-5xl mx-auto space-y-6">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 mb-2 lg:hidden">Document discovery</p>
                <h1 className="text-4xl font-bold text-white lg:hidden">Explore</h1>
                <p className="text-slate-400 mt-1 lg:hidden">Search and browse documents.</p>
              </div>

              <div className="relative">
                <input
                  type="text"
                  placeholder="Search documents by title, person, location, topic..."
                  value={state.query}
                  onChange={(e) => setState((prev) => ({ ...prev, query: e.target.value }))}
                  className="w-full px-6 py-4 rounded-xl bg-slate-800 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                />
                {state.query && (
                  <button
                    onClick={() => setState((prev) => ({ ...prev, query: '' }))}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition"
                  >
                    ✕
                  </button>
                )}
              </div>

              {(state.selectedPeople.size > 0 || state.selectedPlaces.size > 0 || state.selectedYears.size > 0 || state.selectedTags.size > 0) && (
                <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 lg:hidden">
                  <div className="flex flex-wrap gap-2 mb-3">
                    {Array.from(state.selectedPeople).map((p) => (
                      <span key={p} className="px-3 py-1 bg-purple-600/30 text-purple-300 rounded-full text-xs font-medium">{p} ✕</span>
                    ))}
                    {Array.from(state.selectedPlaces).map((p) => (
                      <span key={p} className="px-3 py-1 bg-orange-600/30 text-orange-300 rounded-full text-xs font-medium">{p} ✕</span>
                    ))}
                    {Array.from(state.selectedYears).map((y) => (
                      <span key={y} className="px-3 py-1 bg-blue-600/30 text-blue-300 rounded-full text-xs font-medium">{y} ✕</span>
                    ))}
                    {Array.from(state.selectedTags).map((t) => (
                      <span key={t} className="px-3 py-1 bg-green-600/30 text-green-300 rounded-full text-xs font-medium">{t} ✕</span>
                    ))}
                  </div>
                </div>
              )}

              {loading ? (
                <div className="text-center py-16 text-slate-400">Loading documents...</div>
              ) : filteredDocs.length === 0 ? (
                <div className="text-center py-16">
                  <p className="text-slate-400">No documents found. Try a different search.</p>
                </div>
              ) : (
                <>
                  <div className="text-sm text-slate-400">
                    Showing <span className="font-semibold text-slate-300">{filteredDocs.length}</span> {filteredDocs.length === 1 ? 'document' : 'documents'}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-8">
                    {filteredDocs.map((doc) => {
                      const docId = doc.document_id || doc.id || '';
                      const isSelected = state.selectedDocument?.document_id === docId || state.selectedDocument?.id === docId;

                      return (
                        <button
                          key={docId}
                          onClick={() => setState((prev) => ({ ...prev, selectedDocument: doc }))}
                          className={`p-5 rounded-lg border-2 transition text-left ${
                            isSelected
                              ? 'border-blue-500 bg-blue-950/30 shadow-lg shadow-blue-500/20'
                              : 'border-slate-700 bg-slate-800/40 hover:bg-slate-800/60 hover:border-slate-600'
                          }`}
                        >
                          <h3 className="font-semibold text-white mb-2 line-clamp-2">{doc.title}</h3>
                          {doc.document_date && (
                            <p className="text-xs text-slate-400 mb-3">
                              {new Date(doc.document_date).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </p>
                          )}
                          <p className="text-sm text-slate-300 mb-4 line-clamp-3">{doc.summary}</p>
                          <div className="flex flex-wrap gap-1.5">
                            {(Array.isArray(doc.people) ? doc.people : []).slice(0, 2).map((p) => (
                              <span key={p} className="px-2 py-0.5 text-xs bg-purple-900/30 text-purple-300 rounded">{p}</span>
                            ))}
                            {(Array.isArray(doc.places) ? doc.places : []).slice(0, 2).map((p) => (
                              <span key={p} className="px-2 py-0.5 text-xs bg-orange-900/30 text-orange-300 rounded">{p}</span>
                            ))}
                            {(Array.isArray(doc.topics) ? doc.topics : []).slice(0, 2).map((t) => (
                              <span key={t} className="px-2 py-0.5 text-xs bg-green-900/30 text-green-300 rounded">{t}</span>
                            ))}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          </section>
        </div>

      </main>

      {/* Document Modal */}
      {state.selectedDocument && (
        <DocumentModal
          doc={state.selectedDocument}
          onClose={() => setState((prev) => ({ ...prev, selectedDocument: null }))}
        />
      )}
    </div>
  );
}

export default Explore;
