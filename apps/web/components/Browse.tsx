'use client';

import React, { useState, useEffect, useMemo } from 'react';

interface BrowseProps {
  className?: string;
  send?: (method: string, params: any) => Promise<any>;
  onOpenDocument?: (documentId: string, openOriginal?: boolean) => void;
}

interface Document {
  id: string;
  title: string;
  created_at: string;
  metadata?: Record<string, any>;
}

interface BrowseNode {
  name?: string;
  count?: number;
  year?: number;
  month?: number;
  id?: string;
  children?: BrowseNode[];
}

type BrowseMode = 'explore' | 'date' | 'tags' | 'entities';

const annotateMonthNodes = (year: number, months: BrowseNode[]) =>
  months.map(month => ({ ...month, year }));

export function Browse({ className = '', send, onOpenDocument }: BrowseProps) {
  const [browseMode, setBrowseMode] = useState<BrowseMode>('explore');
  const [hierarchy, setHierarchy] = useState<BrowseNode[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<BrowseNode[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [exploreInput, setExploreInput] = useState('');
  const [exploreSrc, setExploreSrc] = useState('/explore');

  const unwrapToolResult = (payload: any) => {
    let current = payload;
    let depth = 0;

    while (current && typeof current === 'object' && 'result' in current && depth < 6) {
      const next = current.result;
      if (next === undefined) break;
      current = next;
      depth += 1;
    }

    return current || {};
  };

  // Load root hierarchy on mount or mode change
  useEffect(() => {
    void loadRootHierarchy();
    setExpandedNodes(new Set());
    setSelectedPath([]);
    setDocuments([]);
    setSelectedDoc(null);
  }, [browseMode, send]);

  const invokeBrowseTool = async (name: string, arguments_: Record<string, any> = {}) => {
    if (!send) {
      throw new Error('Browse transport is not available');
    }

    return send('tools/invoke', {
      agentId: 'storage-agent',
      name,
      arguments: arguments_,
    });
  };

  const loadRootHierarchy = async () => {
    if (browseMode === 'explore') {
      setHierarchy([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      let endpoint = '';
      if (browseMode === 'date') {
        endpoint = 'browse_by_date';
      } else if (browseMode === 'tags') {
        endpoint = 'browse_by_tags';
      } else if (browseMode === 'entities') {
        endpoint = 'browse_by_entities';
      }

      const result: any = unwrapToolResult(await invokeBrowseTool(endpoint, {}));
      
      // Parse response based on mode
      let nodes: BrowseNode[] = [];
      if (browseMode === 'date' && result.years) {
        nodes = result.years;
      } else if (browseMode === 'tags' && result.tags) {
        nodes = result.tags;
      } else if (browseMode === 'entities' && result.entities) {
        nodes = result.entities;
      }
      
      setHierarchy(nodes);
      console.debug(`[BROWSE] Loaded ${nodes.length} ${browseMode} nodes`);

      if (browseMode === 'date' && nodes.length === 1 && typeof nodes[0].year === 'number') {
        const yearNode = nodes[0];
        const selectedYear = yearNode.year;
        const yearResult: any = await invokeBrowseTool('browse_by_date', { year: selectedYear });
        const months = Array.isArray(yearResult.months) && typeof selectedYear === 'number'
          ? annotateMonthNodes(selectedYear, yearResult.months)
          : [];

        setHierarchy(prev => prev.map(node => (node.year === selectedYear ? { ...node, children: months } : node)));
        setExpandedNodes(typeof selectedYear === 'number' ? new Set([`date-${selectedYear}`]) : new Set());

        const onlyMonth = months.length === 1 ? months[0] : null;
        const selectedMonth = onlyMonth?.month;
        if (typeof selectedYear === 'number' && typeof selectedMonth === 'number') {
          await handleYearMonthClick(selectedYear, selectedMonth);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error(`[BROWSE] Error loading ${browseMode}:`, message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadChildren = async (node: BrowseNode) => {
    const nodeKey = `${browseMode}-${node.year || node.id || node.name}`;
    
    if (expandedNodes.has(nodeKey)) {
      // Collapse
      setExpandedNodes(prev => {
        const next = new Set(prev);
        next.delete(nodeKey);
        return next;
      });
      return;
    }

    setIsLoading(true);
    
    try {
      if (browseMode === 'date' && node.year && !node.month) {
        // Load months for year
        const result: any = unwrapToolResult(await invokeBrowseTool('browse_by_date', { year: node.year }));
        const months = Array.isArray(result.months) ? annotateMonthNodes(node.year, result.months) : [];
        
        // Update hierarchy with months
        setHierarchy(prev => prev.map(n => 
          n.year === node.year ? { ...n, children: months } : n
        ));
        
        setExpandedNodes(prev => new Set(prev).add(nodeKey));
        console.debug(`[BROWSE] Expanded year ${node.year}: found ${months.length} months`);
      } else if (browseMode === 'tags' && node.id) {
        // Load documents for tag
        const result: any = unwrapToolResult(await invokeBrowseTool('browse_by_tag_documents', { tag_id: node.id }));
        setDocuments(result.documents || []);
        setSelectedDoc(null);
        setSearchFilter('');
        setSelectedPath([node]);
        console.debug(`[BROWSE] Loaded ${result.documents?.length || 0} documents for tag`);
      } else if (browseMode === 'entities' && node.name) {
        // Load documents for entity
        const result: any = unwrapToolResult(await invokeBrowseTool('browse_by_entity_documents', { entity_name: node.name }));
        setDocuments(result.documents || []);
        setSelectedDoc(null);
        setSearchFilter('');
        setSelectedPath([node]);
        console.debug(`[BROWSE] Loaded ${result.documents?.length || 0} documents for entity`);
      }

      setExpandedNodes(prev => new Set(prev).add(nodeKey));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error(`[BROWSE] Error expanding node:`, message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleYearMonthClick = async (year: number, month: number) => {
    setIsLoading(true);
    
    try {
      const result: any = unwrapToolResult(await invokeBrowseTool('browse_by_date', { year, month }));
      setDocuments(result.documents || []);
      setSelectedDoc(null);
      setSearchFilter('');
      setSelectedPath([{ year, name: year.toString() }, { year, month, name: `Month ${month}` }]);
      console.debug(`[BROWSE] Loaded ${result.documents?.length || 0} documents for ${year}-${month}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error(`[BROWSE] Error loading month documents:`, message);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredDocuments = useMemo(() => {
    if (!searchFilter) return documents;
    const lower = searchFilter.toLowerCase();
    return documents.filter(doc => 
      doc.title.toLowerCase().includes(lower) || 
      JSON.stringify(doc.metadata).toLowerCase().includes(lower)
    );
  }, [documents, searchFilter]);

  const renderNode = (node: BrowseNode, depth: number = 0) => {
    const nodeKey = `${browseMode}-${node.year || node.month || node.id || node.name}`;
    const isExpanded = expandedNodes.has(nodeKey);
    const hasChildren = node.count ? node.count > 0 : true;

    if (browseMode === 'date' && node.month !== undefined) {
      // Month node - clickable
      return (
        <div key={nodeKey} className="pl-8">
          <button
            onClick={() => node.year && handleYearMonthClick(node.year, node.month!)}
            className="w-full text-left px-3 py-2 rounded hover:bg-slate-800/50 flex items-center gap-2 text-sm font-medium text-slate-100"
          >
            <span className="text-slate-400">📅</span>
            <span className="text-sm text-slate-100">Month {node.month}</span>
            <span className="ml-auto text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
              {node.count || 0}
            </span>
          </button>
        </div>
      );
    }

    return (
      <div key={nodeKey}>
        <button
          onClick={() => loadChildren(node)}
          disabled={!hasChildren}
          className={`w-full text-left px-3 py-2 rounded flex items-center gap-2 text-sm transition ${
            !hasChildren ? 'opacity-50 cursor-default text-slate-400' : 'hover:bg-slate-800/40'
          }`}
        >
          {hasChildren ? (
            isExpanded ? (
              <span className="text-gray-500">▼</span>
            ) : (
              <span className="text-gray-500">▶</span>
            )
          ) : (
            <span className="w-4" />
          )}
          
          {browseMode === 'date' && node.year && (
            <span className="font-medium text-slate-200">{node.year}</span>
          )}
          {browseMode === 'tags' && (
            <span className="text-slate-300">🏷️</span>
          )}
          {browseMode === 'entities' && (
            <span className="text-slate-300">👥</span>
          )}
          
          {(node.name || node.year) && (
            <span className={isExpanded ? 'font-semibold text-slate-100' : 'text-slate-200'}>
              {node.name || node.year}
            </span>
          )}
          
          <span className="ml-auto text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded">
            {node.count || 0}
          </span>
        </button>

        {/* Nested children */}
        {isExpanded && (node as any).children && (
          <div className="ml-2 border-l border-gray-200">
            {(node as any).children.map((child: any) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const modeIcon: Record<BrowseMode, string> = {
    explore: '🔎',
    date: '📅',
    tags: '🏷️',
    entities: '👥'
  };

  return (
    <div className={`flex gap-4 h-full bg-slate-950 text-slate-100 ${className}`}>
      <div className="flex-1 border-r border-slate-800 overflow-auto bg-slate-900/50">
        <div className="p-4 border-b border-slate-800 sticky top-0 bg-slate-950/95 backdrop-blur">
          <div className="flex gap-2 mb-4">
            {(['explore', 'date', 'tags', 'entities'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setBrowseMode(mode)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${
                  browseMode === mode
                    ? 'bg-blue-500/20 text-blue-300 font-medium ring-1 ring-blue-500/40'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>{modeIcon[mode]}</span>
                <span className="capitalize">{mode}</span>
              </button>
            ))}
          </div>
        </div>

        {browseMode === 'explore' ? (
          <div className="h-[calc(100vh-14rem)] min-h-[60vh] rounded-lg overflow-hidden">
            <div className="flex h-full">
              <div className="w-80 border-r border-slate-800 bg-slate-900 p-4">
                <div className="mb-3">
                  <label className="text-xs text-slate-400 mb-2 block">Explore</label>
                  <input
                    type="text"
                    placeholder="Search / Explore..."
                    value={exploreInput}
                    onChange={(e) => setExploreInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') setExploreSrc(`/explore?q=${encodeURIComponent(exploreInput)}`); }}
                    className="w-full px-3 py-2 rounded bg-slate-800 text-slate-100 placeholder:text-slate-400"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setExploreSrc(`/explore?q=${encodeURIComponent(exploreInput)}`)}
                    className="px-3 py-2 bg-blue-600 text-white rounded text-sm"
                  >Search</button>
                  <button
                    onClick={() => { setExploreInput(''); setExploreSrc('/explore'); }}
                    className="px-3 py-2 bg-slate-700 text-slate-200 rounded text-sm"
                  >Reset</button>
                </div>
                <p className="text-xs text-slate-400 mt-3">Use the left panel to search; results appear on the right.</p>
              </div>
              <div className="flex-1 bg-slate-950">
                <iframe src={exploreSrc} className="h-full w-full border-none" title="Explore" />
              </div>
            </div>
          </div>
        ) : ( 
          <>
            {error && (
              <div className="p-4 bg-red-950/50 border border-red-800 text-red-200 rounded-lg m-4">
                Error: {error}
              </div>
            )}

            {isLoading && (
              <div className="p-4 text-center text-slate-400">
                <div className="inline-block animate-spin">⚙️</div>
                <p>Loading...</p>
              </div>
            )}

            {!isLoading && hierarchy.length === 0 && !error && (
              <div className="p-4 text-center text-slate-400">
                No {browseMode} data available
              </div>
            )}

            <div className="p-4 space-y-1">
              {hierarchy.map((node) => renderNode(node))}
            </div>
          </>
        )}
      </div>

      {browseMode !== 'explore' && (
        <>
          <div className="flex-1 flex flex-col border-r border-slate-800 overflow-auto bg-slate-900/40">
            {selectedPath.length > 0 && (
              <div className="p-4 border-b border-slate-800 bg-slate-950/95 sticky top-0 backdrop-blur">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-slate-400">Path:</span>
                  {selectedPath.map((node, i) => (
                    <React.Fragment key={i}>
                      {i > 0 && <span className="text-slate-500">›</span>}
                      <span className="text-sm font-medium text-slate-100 bg-slate-900 px-2 py-1 rounded border border-slate-700">
                        {node.name || node.year || `Month ${node.month}`}
                      </span>
                    </React.Fragment>
                  ))}
                </div>
              </div>
            )}

            {documents.length > 0 && (
              <>
                <div className="p-4 border-b border-gray-200">
                  <div className="relative">
                    <span className="absolute left-3 top-3 text-slate-400">🔍</span>
                    <input
                      type="text"
                      placeholder="Search documents..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    {filteredDocuments.length} of {documents.length} documents
                  </p>
                </div>

                <div className="flex-1 overflow-auto">
                  <div className="space-y-2 p-4">
                    {filteredDocuments.map((doc) => (
                      <button
                        key={doc.id}
                        onClick={() => {
                          if (onOpenDocument) {
                            onOpenDocument(doc.id);
                          } else {
                            setSelectedDoc(doc);
                          }
                        }}
                        className={`w-full text-left p-3 rounded-lg border-2 transition ${
                          selectedDoc?.id === doc.id
                            ? 'border-blue-500/70 bg-blue-500/10'
                            : 'border-slate-700 bg-slate-950/60 hover:border-slate-500 hover:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-slate-400 mt-1 flex-shrink-0">📄</span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-100 truncate text-sm">
                              {doc.title}
                            </p>
                            <p className="text-xs text-slate-400 mt-1">
                              {new Date(doc.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {documents.length === 0 && selectedPath.length > 0 && !isLoading && (
              <div className="flex-1 flex items-center justify-center text-slate-400">
                <p>No documents found</p>
              </div>
            )}

            {documents.length === 0 && selectedPath.length === 0 && (
              <div className="flex-1 flex items-center justify-center text-slate-500">
                <p>Select a {browseMode} to view documents</p>
              </div>
            )}
          </div>

          {selectedDoc && (
            <div className="flex-1 border-l border-slate-800 flex flex-col overflow-auto bg-slate-950/60">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-950/95 backdrop-blur">
                <h3 className="font-semibold text-slate-100">Document Preview</h3>
                <button
                  onClick={() => setSelectedDoc(null)}
                  className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800"
                >
                  ✕
                </button>
              </div>

              <div className="flex-1 overflow-auto p-4 space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-slate-300 mb-2">Title</h4>
                  <p className="text-sm text-slate-100 bg-slate-900 p-3 rounded border border-slate-700">
                    {selectedDoc.title}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-slate-300 mb-2">Created</h4>
                  <p className="text-sm text-slate-100 bg-slate-900 p-3 rounded border border-slate-700">
                    {new Date(selectedDoc.created_at).toLocaleString()}
                  </p>
                </div>

                {selectedDoc.metadata && Object.keys(selectedDoc.metadata).length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-300 mb-2">Metadata</h4>
                    <pre className="text-xs bg-slate-900 p-3 rounded border border-slate-700 overflow-auto max-h-96 text-slate-300">
                      {JSON.stringify(selectedDoc.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Browse;
