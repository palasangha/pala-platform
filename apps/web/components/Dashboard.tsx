'use client';

import Image from 'next/image';
import { useCallback, useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import DocumentBrowser from './DocumentBrowser';
import InlineStepEditor from './InlineStepEditor';

interface DocumentMetadata {
  document?: {
    type?: string;
    title?: string;
    date?: {
      year?: number;
      month?: number;
      day?: number;
      display?: string;
    };
    language?: string;
  };
  people?: Array<{
    name: string;
    role?: string;
    biography?: string;
  }>;
  organizations?: Array<{
    name: string;
    type?: string;
  }>;
  locations?: Array<{
    name: string;
    type?: string;
  }>;
  content?: {
    summary?: string;
    keywords?: string[];
    subjects?: string[];
  };
  analysis?: {
    sentiment?: string;
    themes?: string[];
  };
}

interface ToolDefinition {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  agentId: string;
  metadata?: Record<string, unknown>;
}

interface Agent {
  id: string;
  tools: ToolDefinition[];
}

type WorkflowId = 'document-processing' | 'audio-transcription' | 'search-query';
type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

interface WorkflowStep {
  id: string;
  name: string;
  description: string;
  status: StepStatus;
  data?: unknown;
  error?: string;
  provider?: string; // OCR provider, agent name, etc.
  duration?: number; // Processing time in ms
  editable?: boolean; // Can this step be edited after completion?
}

interface Workflow {
  id: WorkflowId;
  name: string;
  description: string;
  icon: string;
  steps: WorkflowStep[];
  active: boolean;
}

const initialWorkflows: Workflow[] = [
  {
    id: 'document-processing',
    name: 'Document Processing',
    description: 'Convert physical documents to enriched digital content',
    icon: '📄',
    active: true,
    steps: [
      { id: 'upload', name: 'Upload Document', description: 'Upload scanned document or image', status: 'pending', editable: false },
      { id: 'ocr', name: 'OCR Extraction', description: 'Extract text from image', status: 'pending', editable: true },
      { id: 'metadata', name: 'Metadata Enrichment', description: 'Generate structured metadata', status: 'pending', editable: true },
      { id: 'signing', name: 'Digital Signing', description: 'Apply digital signature', status: 'pending', editable: false },
      { id: 'storage', name: 'Store Content', description: 'Save to storage', status: 'pending', editable: false },
    ]
  },
  {
    id: 'audio-transcription',
    name: 'Audio Transcription',
    description: 'Transcribe and enrich audio recordings',
    icon: '🎤',
    active: false,
    steps: [
      { id: 'upload', name: 'Upload Audio', description: 'Upload audio file', status: 'pending' },
      { id: 'transcribe', name: 'Transcription', description: 'Convert speech to text using Scribe agent', status: 'pending' },
      { id: 'language', name: 'Language Detection', description: 'Identify language and dialect', status: 'pending' },
      { id: 'metadata', name: 'Metadata Enrichment', description: 'Extract speaker info, topics, etc.', status: 'pending' },
      { id: 'review', name: 'Human Review', description: 'Verify transcription accuracy', status: 'pending' },
      { id: 'storage', name: 'Store Content', description: 'Save transcription and metadata', status: 'pending' },
    ]
  },
  {
    id: 'search-query',
    name: 'Content Search',
    description: 'Intelligent search across all content',
    icon: '🔍',
    active: false,
    steps: [
      { id: 'query', name: 'Enter Query', description: 'Natural language or keyword search', status: 'pending' },
      { id: 'search', name: 'Search Execution', description: 'Search across indexed content', status: 'pending' },
      { id: 'results', name: 'View Results', description: 'Browse and filter results', status: 'pending' },
    ]
  }
];

export default function Dashboard() {
  const [wsUrl, setWsUrl] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      setWsUrl(`${protocol}//${host}:3000`);
    }
  }, []);

  const { connected, send } = useWebSocket(wsUrl);

  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>(initialWorkflows);
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowId>('document-processing');
  
  // Document Processing State
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentFileName, setDocumentFileName] = useState<string>('');
  const [documentPreviewUrl, setDocumentPreviewUrl] = useState<string>('');
  const [ocrText, setOcrText] = useState<string>('');
  const [ocrLines, setOcrLines] = useState<Array<{ text: string; confidence: number }>>([]);
  const [ocrProgress, setOcrProgress] = useState<number>(0);
  const [extractedMetadata, setExtractedMetadata] = useState<DocumentMetadata | null>(null);
  
  // Storage configuration
  const [availableBackends, setAvailableBackends] = useState<Array<{ name: string; type: string; is_default: boolean }>>([]);
  const [selectedBackend, setSelectedBackend] = useState<string>('');
  
  // UI State
  const [currentView, setCurrentView] = useState<'workflow' | 'browse'>('workflow');
  const [expandedStep, setExpandedStep] = useState<string | null>(null); // Which step is expanded for editing
  const [editingStep, setEditingStep] = useState<string | null>(null); // Which step is being edited

  const loadAvailableBackends = useCallback(async () => {
    if (!connected) {
      return;
    }
    
    try {
      const result = await send('tools/invoke', {
        name: 'list_backends',
        agentId: 'storage-agent',
        arguments: {}
      }) as any;

      const data = result?.result || result;
      setAvailableBackends(data.backends || [{ name: 'local-primary', type: 'LocalStorageBackend', is_default: true }]);
      
      // Set default backend
      const defaultBackend = data.backends?.find((b: any) => b.is_default)?.name || data.default_backend || 'local-primary';
      setSelectedBackend(defaultBackend);
    } catch (err) {
      console.error('Error loading backends:', err);
      // Set default on error
      setAvailableBackends([{ name: 'local-primary', type: 'LocalStorageBackend', is_default: true }]);
      setSelectedBackend('local-primary');
    }
  }, [connected, send]);

  const refreshData = useCallback(async () => {
    try {
      setError(null);

      const [agentsData, toolsData] = await Promise.all([
        send('agents/list', {}),
        send('tools/list', {}),
      ]);

      const agentsResponse = agentsData as { agents?: Agent[] };
      const toolsResponse = toolsData as { tools?: ToolDefinition[] };

      const mergedTools = (toolsResponse.tools || []).map((tool) => {
        const agentMatch = agentsResponse.agents?.find((agent) => agent.id === tool.agentId);
        return {
          ...tool,
          description: tool.description || (agentMatch ? `${agentMatch.id} tool` : 'Agent tool'),
        };
      });

      setTools(mergedTools);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    }
  }, [send]);

  useEffect(() => {
    if (connected) {
      refreshData();
      loadAvailableBackends();
    }
  }, [connected, refreshData, loadAvailableBackends]);

  useEffect(() => {
    if (!documentPreviewUrl) {
      return;
    }

    return () => {
      URL.revokeObjectURL(documentPreviewUrl);
    };
  }, [documentPreviewUrl]);

  const updateStepStatus = (workflowId: WorkflowId, stepId: string, status: StepStatus, data?: unknown, error?: string, provider?: string, duration?: number) => {
    setWorkflows(prev => prev.map(wf => {
      if (wf.id === workflowId) {
        return {
          ...wf,
          steps: wf.steps.map(step => 
            step.id === stepId ? { ...step, status, data, error, provider, duration } : step
          )
        };
      }
      return wf;
    }));
  };

  const handleRunOCR = async () => {
    if (!documentFile) {
      setError('Please upload a document image');
      return;
    }

    updateStepStatus('document-processing', 'upload', 'completed');
    updateStepStatus('document-processing', 'ocr', 'running');

    const startTime = Date.now();
    setOcrLines([]);
    try {
      const { createWorker } = await import('tesseract.js');
      const worker = await createWorker('eng');

      const { data } = await worker.recognize(documentFile);
      await worker.terminate();

      const extractedText = data?.text?.trim() || '';
      const lineConfidence = (data?.lines || [])
        .map((line) => ({
          text: line.text.trim(),
          confidence: typeof line.confidence === 'number' ? line.confidence : 0,
        }))
        .filter((line) => line.text.length > 0);
      const duration = Date.now() - startTime;
      setOcrText(extractedText);
      setOcrLines(lineConfidence);
      setOcrProgress(100);
      updateStepStatus('document-processing', 'ocr', 'completed',
        { text: extractedText, confidence: data?.confidence, lines: lineConfidence },
        undefined,
        'Tesseract.js (browser)',
        duration
      );
      updateStepStatus('document-processing', 'metadata', 'pending');
      
      // Auto-expand OCR step to show results
      setExpandedStep('ocr');
    } catch (err) {
      updateStepStatus('document-processing', 'ocr', 'failed', undefined, err instanceof Error ? err.message : 'OCR failed');
      setError(err instanceof Error ? err.message : 'OCR processing failed');
    }
  };

  const handleExtractMetadata = async () => {
    if (!ocrText.trim()) {
      setError('No OCR text available. Run OCR first.');
      return;
    }

    if (!connected) {
      setError('WebSocket not connected. Please wait for the connection to establish.');
      console.log('WebSocket connection status:', { connected, wsUrl });
      return;
    }

    const metadataTool = tools.find(t => t.name === 'extract_metadata');
    if (!metadataTool) {
      setError('Metadata extraction tool not available. No agent tools loaded.');
      console.log('Available tools:', tools.map(t => t.name));
      return;
    }

    updateStepStatus('document-processing', 'metadata', 'running');

    const startTime = Date.now();
    try {
      console.log('Invoking metadata extraction tool:', metadataTool.name);
      const result = await send('tools/invoke', {
        toolName: metadataTool.name,
        agentId: metadataTool.agentId,
        arguments: {
          ocr_text: ocrText,
          model: 'claude',
          output_type: 'combined',
          language: 'en',
          document_context: 'historical_letter',
        },
      });

      const duration = Date.now() - startTime;
      setExtractedMetadata(result as DocumentMetadata);
      
      const providerLabel = metadataTool.metadata?.provider || metadataTool.agentId || metadataTool.name;

      updateStepStatus('document-processing', 'metadata', 'completed', result, undefined, `MCP Agent: ${providerLabel}`, duration);
      updateStepStatus('document-processing', 'signing', 'pending');
      
      // Auto-expand metadata step to show results
      setExpandedStep('metadata');
    } catch (err) {
      console.error('Metadata extraction error:', err);
      updateStepStatus('document-processing', 'metadata', 'failed', undefined, err instanceof Error ? err.message : 'Metadata extraction failed');
      setError(err instanceof Error ? err.message : 'Metadata extraction failed');
    }
  };



  // Function to edit a specific step
  const handleEditStep = (stepId: string) => {
    setEditingStep(stepId);
    setExpandedStep(stepId);
  };

  // Function to save edits for a step
  const handleSaveStepEdits = (stepId: string) => {
    setEditingStep(null);
    // Update the step to mark it as edited
    if (stepId === 'ocr') {
      updateStepStatus('document-processing', 'ocr', 'completed', 
        { text: ocrText, confidence: 0.95, edited: true }
      );
    } else if (stepId === 'metadata') {
      updateStepStatus('document-processing', 'metadata', 'completed', 
        extractedMetadata,
        undefined,
        currentWorkflow?.steps.find(s => s.id === 'metadata')?.provider,
        currentWorkflow?.steps.find(s => s.id === 'metadata')?.duration
      );
    }
  };

  const handleCancelStepEdits = () => {
    setEditingStep(null);
    // Reset to original values if needed
  };

  const handleSign = async () => {
    updateStepStatus('document-processing', 'signing', 'running');
    
    // Simulate signing process
    await new Promise(resolve => setTimeout(resolve, 500));
    
    updateStepStatus('document-processing', 'signing', 'completed', { 
      signature: `sig_${Date.now()}`,
      timestamp: new Date().toISOString(),
      algorithm: 'SHA-256'
    });
    updateStepStatus('document-processing', 'storage', 'pending');
  };

  const handleStore = async () => {
    if (!ocrText || !extractedMetadata) {
      setError('No data to store. Complete OCR and metadata extraction first.');
      return;
    }

    if (!connected) {
      setError('WebSocket not connected. Please wait for the connection to establish.');
      return;
    }

    updateStepStatus('document-processing', 'storage', 'running');
    
    try {
      const payload = {
        name: 'store_document',
        agentId: 'storage-agent',
        arguments: {
          job_id: `job-${Date.now()}`,
          file_index: 0,
          ocr_text: ocrText,
          enriched_metadata: extractedMetadata,
          original_file_path: documentFileName,
          backend: selectedBackend,
        },
      };
      console.log('[MCP] Sending store_document payload:', payload);
      const result = await send('tools/invoke', payload) as any;
      console.log('[MCP] Received backend response:', result);

      // Check for backend error or success: false
      if (result?.error || result?.success === false) {
        const errorMsg = result?.error?.message || result?.error || 'Storage failed';
        updateStepStatus('document-processing', 'storage', 'failed', result, errorMsg);
        setError(errorMsg);
        return;
      }

      const data = result?.result || result;
      updateStepStatus('document-processing', 'storage', 'completed', data);
    } catch (err) {
      updateStepStatus('document-processing', 'storage', 'failed', undefined, err instanceof Error ? err.message : 'Storage failed');
      setError(err instanceof Error ? err.message : 'Storage failed');
    }
  };

  const handleResetWorkflow = () => {
    setWorkflows(initialWorkflows);
    setOcrText('');
    setOcrLines([]);
    setExtractedMetadata(null);
    setDocumentFile(null);
    setDocumentFileName('');
    setDocumentPreviewUrl('');
    setError(null);
  };

  const currentWorkflow = workflows.find(w => w.id === activeWorkflow);
  const currentStepIndex = currentWorkflow?.steps.findIndex(s => s.status === 'pending' || s.status === 'running') ?? 0;

  const getStepStatusColor = (status: StepStatus) => {
    switch (status) {
      case 'completed': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'running': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed': return 'bg-red-100 text-red-800 border-red-200';
      case 'skipped': return 'bg-slate-100 text-slate-600 border-slate-200';
      default: return 'bg-slate-50 text-slate-500 border-slate-200';
    }
  };

  const getStepIcon = (status: StepStatus) => {
    switch (status) {
      case 'completed': return '✓';
      case 'running': return '⟳';
      case 'failed': return '✕';
      case 'skipped': return '−';
      default: return '○';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      {/* Show Document Browser */}
      {currentView === 'browse' && (
        <div className="fixed inset-0 z-40">
          <div className="h-full flex flex-col bg-white">
            {/* Browser Header */}
            <div className="bg-white border-b border-slate-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold text-slate-900">Pala Platform</h1>
                  <p className="text-sm text-slate-600">Browse Stored Documents</p>
                </div>
                <button
                  onClick={() => setCurrentView('workflow')}
                  className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300"
                >
                  Back to Workflow
                </button>
              </div>
            </div>
            <div className="flex-1">
              <DocumentBrowser />
            </div>
          </div>
        </div>
      )}

      {/* Main Workflow View */}
      {currentView === 'workflow' && (
        <>
          {/* Header */}
          <nav className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">Pala Platform</h1>
              <p className="text-sm text-slate-600">Digital Preservation Workflows</p>
            </div>
            <div className="flex items-center gap-3">
              {/* View Switcher */}
              <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
                <button
                  onClick={() => setCurrentView('workflow')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'workflow'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Workflow
                </button>
                <button
                  onClick={() => setCurrentView('browse')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    currentView === 'browse'
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Browse
                </button>
              </div>
              
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50">
                <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                <span className="text-xs font-medium text-slate-600">{connected ? 'Connected' : 'Offline'}</span>
              </div>
              <button
                onClick={refreshData}
                className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Sync Agents
              </button>
            </div>
          </div>
        </div>
      </nav>

      {error && (
        <div className="max-w-7xl mx-auto px-6 pt-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Workflow Selector */}
          <div className="col-span-3">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-4">Workflows</h2>
              <div className="space-y-2">
                {workflows.map(workflow => (
                  <button
                    key={workflow.id}
                    onClick={() => setActiveWorkflow(workflow.id)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                      activeWorkflow === workflow.id
                        ? 'border-blue-500 bg-blue-50 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{workflow.icon}</span>
                      <div className="flex-1">
                        <p className="font-semibold text-slate-900 text-sm">{workflow.name}</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600">{workflow.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="col-span-9">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
              {/* Workflow Header */}
              <div className="border-b border-slate-200 px-6 py-5 bg-gradient-to-r from-blue-50 to-indigo-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{currentWorkflow?.icon}</span>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900">{currentWorkflow?.name}</h2>
                      <p className="text-sm text-slate-600 mt-1">{currentWorkflow?.description}</p>
                    </div>
                  </div>
                  <button
                    onClick={handleResetWorkflow}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                  >
                    Reset Workflow
                  </button>
                </div>
              </div>

              {/* Pipeline Steps Timeline - Interactive */}
              <div className="px-6 py-5 border-b border-slate-200 bg-slate-50">
                <div className="flex items-center gap-2">
                  {currentWorkflow?.steps.map((step, idx) => (
                    <div key={step.id} className="flex items-center flex-1">
                      <div
                        onClick={() => step.status === 'completed' || step.status === 'failed' ? setExpandedStep(expandedStep === step.id ? null : step.id) : null}
                        className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${getStepStatusColor(step.status)} ${
                          step.status !== 'pending' ? 'cursor-pointer hover:shadow-md' : 'cursor-not-allowed'
                        } ${expandedStep === step.id ? 'ring-2 ring-blue-400' : ''}`}
                      >
                        <span className="font-mono text-sm">{getStepIcon(step.status)}</span>
                        <div className="flex-1 text-left">
                          <div className="text-xs font-medium truncate">{step.name}</div>
                          {step.provider && (
                            <div className="text-[10px] text-slate-500 truncate">{step.provider}</div>
                          )}
                        </div>
                        {step.editable && step.status === 'completed' && (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditStep(step.id);
                            }}
                            className="ml-auto p-1 hover:bg-white/50 rounded cursor-pointer"
                            title="Edit this step"
                          >
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </div>
                        )}
                      </div>
                      {idx < (currentWorkflow?.steps.length ?? 0) - 1 && (
                        <svg className="w-4 h-4 text-slate-300 mx-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Workflow Content - Unified Step Display */}
              <div className="p-6 space-y-4">
                {activeWorkflow === 'document-processing' && (
                  <>
                    {/* Upload Step */}
                    <div className={`rounded-xl border-2 overflow-hidden ${currentStepIndex === 0 ? 'border-blue-500' : 'border-slate-200'}`}>
                      <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-slate-900">📤 Upload Document</h3>
                            <p className="text-xs text-slate-600 mt-0.5">Step 1 of 5</p>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStepStatusColor(currentWorkflow?.steps[0].status || 'pending')}`}>
                            {currentWorkflow?.steps[0].status}
                          </span>
                        </div>
                      </div>
                      <div className="p-5 bg-white">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={(event) => {
                            const file = event.target.files?.[0] || null;
                            setDocumentFile(file);
                            setDocumentFileName(file?.name || '');
                            setDocumentPreviewUrl(file ? URL.createObjectURL(file) : '');
                          }}
                          className="w-full px-4 py-2 border border-slate-300 rounded-lg mb-3 bg-white"
                        />
                        {documentFile && (
                          <div className="mb-3 text-xs text-slate-600">
                            Selected: {documentFileName} • {(documentFile.size / 1024).toFixed(1)} KB
                          </div>
                        )}
                        {documentPreviewUrl && (
                          <div className="mb-3">
                            <Image
                              src={documentPreviewUrl}
                              alt="Uploaded document preview"
                              width={640}
                              height={480}
                              unoptimized
                              className="max-h-48 w-auto rounded-lg border border-slate-200"
                            />
                          </div>
                        )}
                        <button
                          onClick={handleRunOCR}
                          disabled={!documentFile || currentWorkflow?.steps[0].status === 'completed'}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed font-medium text-sm"
                        >
                          Upload & Run OCR
                        </button>
                      </div>
                    </div>

                    {/* OCR Step */}
                    {currentWorkflow?.steps[1].status !== 'pending' && (
                      <div className={`rounded-xl border-2 overflow-hidden ${expandedStep === 'ocr' ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200'}`}>
                        <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h3 className="font-semibold text-slate-900">👁️ OCR Extraction</h3>
                              <div className="flex items-center gap-3 mt-0.5">
                                <p className="text-xs text-slate-600">Step 2 of 5</p>
                                {currentWorkflow?.steps[1].provider && (
                                  <span className="text-xs text-blue-600 font-medium">
                                    • {currentWorkflow.steps[1].provider}
                                  </span>
                                )}
                                {currentWorkflow?.steps[1].duration && (
                                  <span className="text-xs text-slate-500">
                                    • {(currentWorkflow.steps[1].duration / 1000).toFixed(1)}s
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-1 rounded text-xs font-medium ${getStepStatusColor(currentWorkflow?.steps[1].status || 'pending')}`}>
                                {currentWorkflow?.steps[1].status}
                              </span>
                              {currentWorkflow?.steps[1].status === 'completed' && (
                                <button
                                  onClick={() => handleEditStep('ocr')}
                                  className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded border border-blue-200"
                                >
                                  Edit
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="p-5 bg-white">
                          {currentWorkflow?.steps[1].status === 'running' ? (
                            <div className="space-y-3">
                              <div className="flex items-center gap-2 text-blue-600">
                                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span className="text-sm font-medium">Processing document...</span>
                              </div>
                              <div className="h-2 w-full rounded-full bg-slate-200">
                                <div
                                  className="h-2 rounded-full bg-blue-600 transition-all animate-pulse"
                                  style={{ width: '60%' }}
                                />
                              </div>
                            </div>
                          ) : editingStep === 'ocr' ? (
                            <InlineStepEditor
                              stepId="ocr"
                              ocrText={ocrText}
                              metadata={extractedMetadata || {}}
                              onSave={(newText) => {
                                setOcrText(newText);
                                handleSaveStepEdits('ocr');
                              }}
                              onCancel={handleCancelStepEdits}
                            />
                          ) : (
                            <div className="space-y-3">
                              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                                <pre className="text-sm text-slate-900 whitespace-pre-wrap max-h-40 overflow-y-auto">{ocrText}</pre>
                              </div>
                              {ocrLines.length > 0 && (
                                <div className="bg-white border border-slate-200 rounded-lg p-4">
                                  <p className="text-xs font-semibold text-slate-700 mb-2">Line Confidence</p>
                                  <div className="space-y-2 max-h-48 overflow-y-auto">
                                    {ocrLines.map((line, index) => (
                                      <div key={`${line.text}-${index}`} className="flex items-start justify-between gap-3 text-xs text-slate-700">
                                        <span className="flex-1">{line.text}</span>
                                        <span className="text-slate-500">{line.confidence.toFixed(1)}%</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {currentWorkflow?.steps[2].status === 'pending' && (
                                <button
                                  onClick={handleExtractMetadata}
                                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                                >
                                  Extract Metadata
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Metadata Step */}
                    {currentWorkflow?.steps[2].status !== 'pending' && (
                      <div className={`rounded-xl border-2 overflow-hidden ${expandedStep === 'metadata' ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200'}`}>
                        <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h3 className="font-semibold text-slate-900">🏷️ Metadata Enrichment</h3>
                              <div className="flex items-center gap-3 mt-0.5">
                                <p className="text-xs text-slate-600">Step 3 of 5</p>
                                {currentWorkflow?.steps[2].provider && (
                                  <span className="text-xs text-blue-600 font-medium">
                                    • {currentWorkflow.steps[2].provider}
                                  </span>
                                )}
                                {currentWorkflow?.steps[2].duration && (
                                  <span className="text-xs text-slate-500">
                                    • {(currentWorkflow.steps[2].duration / 1000).toFixed(1)}s
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-1 rounded text-xs font-medium ${getStepStatusColor(currentWorkflow?.steps[2].status || 'pending')}`}>
                                {currentWorkflow?.steps[2].status}
                              </span>
                              {currentWorkflow?.steps[2].status === 'completed' && (
                                <button
                                  onClick={() => handleEditStep('metadata')}
                                  className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded border border-blue-200"
                                >
                                  Edit
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="p-5 bg-white">
                          {currentWorkflow?.steps[2].status === 'running' ? (
                            <div className="flex items-center gap-2 text-blue-600">
                              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              <span className="text-sm font-medium">Extracting metadata...</span>
                            </div>
                          ) : editingStep === 'metadata' ? (
                            <InlineStepEditor
                              stepId="metadata"
                              ocrText={ocrText}
                              metadata={extractedMetadata || {}}
                              onSave={(_text, newMetadata) => {
                                setExtractedMetadata(newMetadata);
                                handleSaveStepEdits('metadata');
                              }}
                              onCancel={handleCancelStepEdits}
                            />
                          ) : (
                            <div className="space-y-3">
                              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                                <pre className="text-sm text-slate-900 whitespace-pre-wrap max-h-60 overflow-y-auto">
                                  {JSON.stringify(extractedMetadata, null, 2)}
                                </pre>
                              </div>
                              {currentWorkflow?.steps[2].status === 'completed' && (
                                <button
                                  onClick={handleSign}
                                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                                >
                                  Continue to Signing
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Signing Step */}
                    {currentWorkflow?.steps[2].status === 'completed' && (
                      <div className="rounded-xl border-2 border-slate-200 overflow-hidden">
                        <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <h3 className="font-semibold text-slate-900">🔏 Digital Signing</h3>
                              <p className="text-xs text-slate-600 mt-0.5">Step 4 of 5</p>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getStepStatusColor(currentWorkflow?.steps[3].status || 'pending')}`}>
                              {currentWorkflow?.steps[3].status}
                            </span>
                          </div>
                        </div>
                        {currentWorkflow?.steps[3].status === 'pending' && currentWorkflow?.steps[2].status === 'completed' && (
                          <div className="p-5 bg-white">
                            <button
                              onClick={handleSign}
                              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                            >
                              Sign Document
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Storage Step */}
                    {(currentWorkflow?.steps[3].status === 'completed' || currentWorkflow?.steps[4].status !== 'pending') && (
                      <div className="rounded-xl border-2 border-slate-200 overflow-hidden">
                        <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <h3 className="font-semibold text-slate-900">💾 Store Content</h3>
                              <p className="text-xs text-slate-600 mt-0.5">Step 5 of 5</p>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getStepStatusColor(currentWorkflow?.steps[4].status || 'pending')}`}>
                              {currentWorkflow?.steps[4].status}
                            </span>
                          </div>
                        </div>
                        {currentWorkflow?.steps[4].status === 'pending' && currentWorkflow?.steps[3].status === 'completed' ? (
                          <div className="p-5 bg-white space-y-4">
                            {availableBackends.length > 1 && (
                              <div>
                                <label className="block text-xs font-semibold text-slate-700 mb-2">
                                  Storage Backend
                                </label>
                                <select
                                  value={selectedBackend}
                                  onChange={(e) => setSelectedBackend(e.target.value)}
                                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                  {availableBackends.map((backend) => (
                                    <option key={backend.name} value={backend.name}>
                                      {backend.name} ({backend.type}) {backend.is_default ? '(default)' : ''}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            )}
                            <button
                              onClick={handleStore}
                              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
                            >
                              Store Document
                            </button>
                          </div>
                        ) : currentWorkflow?.steps[4].status === 'completed' ? (
                          <div className="p-5 bg-emerald-50 border-t border-emerald-200">
                            <p className="text-sm text-emerald-700 mb-2">
                              {currentWorkflow?.steps[4].data?.deduplication
                                ? '⚠️ Document already exists (deduplicated)'
                                : '✅ Document successfully stored'}
                            </p>
                            <pre className="text-xs text-emerald-900 bg-white p-3 rounded border border-emerald-200">
                              {JSON.stringify(currentWorkflow?.steps[4].data, null, 2)}
                            </pre>
                            <details className="mt-2">
                              <summary className="cursor-pointer text-xs text-slate-600">Show raw backend response</summary>
                              <pre className="text-xs bg-slate-100 text-slate-800 p-2 rounded border border-slate-200 mt-1">
                                {JSON.stringify(currentWorkflow?.steps[4].data, null, 2)}
                              </pre>
                            </details>
                          </div>
                        ) : null}
                      </div>
                    )}
                  </>
                )}

                {activeWorkflow !== 'document-processing' && (
                  <div className="text-center py-12">
                    <p className="text-slate-500">This workflow is under development</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      </>
      )}
    </div>
  );
}
