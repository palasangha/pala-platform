'use client';

import { useRef, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ContentBrowser } from './ContentBrowser';

type Tab = 'storage' | 'developer' | 'chat';

export function PalaWebDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('developer');
  const { connected } = useWebSocket();

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-950 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Pala Platform</h1>
                <p className="text-xs text-slate-400">Unified Storage & Services Layer</p>
              </div>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                connected ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'
              }`}
            >
              {connected ? '● Connected' : '● Disconnected'}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex gap-1 border-b border-slate-800">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'chat'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('developer')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'developer'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Developer
            </button>
            <button
              onClick={() => setActiveTab('storage')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'storage'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300'
              }`}
            >
              Storage Explorer
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'chat' && <ChatPanel onOpenStorageExplorer={() => setActiveTab('storage')} />}
        {activeTab === 'developer' && <DeveloperPanel />}
        {activeTab === 'storage' && <StorageExplorer />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-xs text-slate-500">
          <p>Pala Platform · {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}

// Developer Panel - Interactive tool testing with code examples
function DeveloperPanel() {
  const [expandedGuide, setExpandedGuide] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileBase64, setFileBase64] = useState<string>('');

  // Handle file selection, convert to base64, and auto-populate JSON input
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] || null;
        setSelectedFile(file);
        setFileBase64('');
        if (file && (
          currentTool?.name === 'store_document' ||
          currentTool?.name === 'process_and_store_document' ||
          currentTool?.name === 'extract_metadata'
        )) {
          const reader = new FileReader();
          reader.onload = () => {
            const arrayBuffer = reader.result as ArrayBuffer;
            const bytes = new Uint8Array(arrayBuffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
              binary += String.fromCharCode(bytes[i]);
            }
            const base64Data = btoa(binary);
            setFileBase64(base64Data);
            
            // Auto-populate fields based on selected tool
            let json: any = {};
            
            if (currentTool?.name === 'store_document') {
              // Auto-populate all required fields for store_document
              const toolDef = AGENTS.find(a => a.id === 'storage-agent')?.tools.find(t => t.name === 'store_document');
              if (toolDef) {
                toolDef.schemaFields.forEach(field => {
                  if (field.name === 'original_file_data') {
                    json.original_file_data = base64Data;
                  } else if (field.name === 'original_file') {
                    json.original_file = file.name;
                  } else if (field.name === 'file_format') {
                    // Try to infer from file extension
                    const ext = file.name.split('.').pop()?.toLowerCase() || '';
                    json.file_format = ['pdf','txt','json','md','jpg','png'].includes(ext) ? ext : 'bin';
                  } else if (field.name === 'type') {
                    json.type = field.possibleValues?.[0] || 'ocr';
                  } else if (field.name === 'created_by') {
                    json.created_by = field.defaultValue || 'web-dashboard';
                  } else if (field.name === 'processed_data') {
                    json.processed_data = 'uploaded via dashboard';
                  } else if (field.name === 'metadata') {
                    json.metadata = {};
                  } else if (field.name === 'app_data') {
                    json.app_data = {};
                  }
                });
              }
              // Always include file MIME type for reference
              json.original_file_mime = file.type || '';
            } else if (currentTool?.name === 'process_and_store_document') {
              // Auto-populate for orchestration tool
              const ext = file.name.split('.').pop()?.toLowerCase() || '';
              json = {
                original_file: base64Data,
                original_file_name: file.name,
                file_format: ['pdf','txt','json','md','jpg','png'].includes(ext) ? ext : 'bin',
                document_type: 'ocr',
                created_by: 'web-dashboard',
              };
            } else if (currentTool?.name === 'extract_metadata') {
              // Auto-populate for extract_metadata by sending full file payload
              const ext = file.name.split('.').pop()?.toLowerCase() || '';
              json = {
                file_data: base64Data,
                filename: file.name,
                file_format: ext || 'bin',
                model: 'ollama',
                output_type: 'pala',
                document_context: 'uploaded_file',
              };
            }
            
            setInput(JSON.stringify(json, null, 2));
            console.log(`[PalaWebDashboard] File loaded and JSON auto-populated for ${currentTool?.name}`);
          };
          reader.onerror = (e) => {
            console.error('[PalaWebDashboard] FileReader error:', e);
          };
          reader.readAsArrayBuffer(file);
        }
      };
    // File picker state and handler are correct above. No unreachable return statements remain in helpers.
  const [selectedAgent, setSelectedAgent] = useState<string>('sample-agent');
  const [selectedTool, setSelectedTool] = useState<string>('echo');
  const [selectedExampleIndex, setSelectedExampleIndex] = useState<number>(0);
  const [input, setInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { client } = useWebSocket();

  type ToolExample = {
    label: string;
    input: string;
  };

  type ToolField = {
    name: string;
    type: string;
    required?: boolean;
    description: string;
    possibleValues?: string[];
    defaultValue?: string;
  };

  type ToolDef = {
    name: string;
    description: string;
    placeholder: string;
    examples: ToolExample[];
    schemaFields: ToolField[];
  };

  type AgentDef = {
    id: string;
    name: string;
    tools: ToolDef[];
  };

  const AGENTS: AgentDef[] = [
    {
      id: 'sample-agent',
      name: 'Sample Agent',
      tools: [
        {
          name: 'echo',
          description: 'Echo back input text',
          placeholder: 'Enter JSON: {"text": "Hello World"}',
          examples: [
            { label: 'Simple greeting', input: '{"text": "Hello World"}' },
            { label: 'Long paragraph', input: '{"text": "This is a longer sample message for echo testing."}' },
          ],
          schemaFields: [
            {
              name: 'text',
              type: 'string',
              required: true,
              description: 'Text that the tool echoes back unchanged.',
            },
          ],
        },
        {
          name: 'sum',
          description: 'Sum array of numbers',
          placeholder: 'Enter JSON: {"numbers": [1, 2, 3]}',
          examples: [
            { label: 'Basic integers', input: '{"numbers": [1, 2, 3, 4, 5]}' },
            { label: 'Mixed values', input: '{"numbers": [10, -2, 3.5, 8]}' },
          ],
          schemaFields: [
            {
              name: 'numbers',
              type: 'number[]',
              required: true,
              description: 'Array of numeric values to sum.',
            },
          ],
        },
        {
          name: 'process_and_store_document',
          description: 'Orchestration: Extract metadata from file and store with metadata',
          placeholder: 'Enter JSON: {"original_file": "base64...", "original_file_name": "document.pdf", "file_format": "pdf", "document_type": "ocr"}',
          examples: [
            {
              label: 'Process PDF (from file upload)',
              input: '{"original_file": "[will be populated with file data]", "original_file_name": "document.pdf", "file_format": "pdf", "document_type": "ocr", "created_by": "web-dashboard"}',
            },
            {
              label: 'Process document with custom type',
              input: '{"original_file": "[base64 encoded file]", "original_file_name": "metadata.json", "file_format": "json", "document_type": "metadata", "created_by": "sample-agent"}',
            },
          ],
          schemaFields: [
            {
              name: 'original_file',
              type: 'string (base64)',
              required: true,
              description: 'Base64-encoded file content.',
            },
            {
              name: 'original_file_name',
              type: 'string',
              required: true,
              description: 'Original filename (e.g., "document.pdf").',
            },
            {
              name: 'file_format',
              type: 'string',
              required: true,
              description: 'File format/extension (e.g., "pdf", "json", "txt").',
              possibleValues: ['pdf', 'txt', 'json', 'jpg', 'png'],
            },
            {
              name: 'document_type',
              type: 'string',
              required: true,
              description: 'Type of document for storage categorization.',
              possibleValues: ['ocr', 'transcription', 'metadata', 'translation', 'note'],
            },
            {
              name: 'created_by',
              type: 'string',
              description: 'Creator identifier for audit trail.',
              defaultValue: 'sample-agent',
            },
          ],
        },
      ],
    },
    {
      id: 'metadata-extraction-agent',
      name: 'Metadata Extraction Agent',
      tools: [
        {
          name: 'extract_metadata',
          description: 'Extract metadata from text',
          placeholder: 'Upload a file or enter JSON with text/file_data, model, output_type',
          examples: [
            {
              label: 'Letter (Pala schema)',
              input: '{"text": "Dear Dr. Smith,\\n\\nI am writing to you regarding the upcoming conference on Digital Humanities to be held in New Delhi on March 15, 2024.\\n\\nAs discussed in our previous meeting, I would like to present our research on using AI for manuscript analysis.\\n\\nBest regards,\\nProf. Kumar", "model": "ollama", "output_type": "pala"}',
            },
            {
              label: 'Goenka Vipassana Letter',
              input: '{"text": "Letter to Dhamma Kamma Vipassana Centre Administration\\n\\nDate: 15th March 2024\\nFrom: Dr. Rajesh Kumar, Department of Buddhist Philosophy\\nTo: The Director, Dhamma Kamma Vipassana Centre, Igatpuri\\n\\nDear Venerable Director,\\n\\nI am writing to initiate a research collaboration between Delhi University and your centre.\\n\\nOur research focuses on Satya Narayan Goenka (1924-2013), who dedicated his life to spreading Vipassana meditation - the ancient technique discovered by Gautama Buddha approximately 2500 years ago.\\n\\nGoenka lineage traces to Sayagyi U Ba Khin, preserving authentic Buddhist teachings. Through his efforts, Vipassana centers have been established globally, with major centers in Kulu, Igatpuri, and Bangalore.\\n\\nWith deep respect,\\nDr. Rajesh Kumar", "model": "ollama", "output_type": "pala", "language": "en", "document_context": "formal_letter"}',
            },
            {
              label: 'Buddhist text (Combined)',
              input: '{"text": "The Buddha taught the Five Precepts: abstaining from killing, stealing, sexual misconduct, false speech, and intoxicants. Practicing these cultivates compassion and mindfulness.", "model": "ollama", "output_type": "combined", "language": "en", "document_context": "dharma-teaching"}',
            },
            {
              label: 'Archipelago format',
              input: '{"text": "Temple record dated 1898 mentioning repairs, donors, and monks in residence.", "model": "ollama", "output_type": "archipelago"}',
            },
          ],
          schemaFields: [
            {
              name: 'text',
              type: 'string',
              description: 'Input text to analyze (OCR, transcription, or any text source). Optional if file_data is provided.',
            },
            {
              name: 'file_data',
              type: 'string',
              description: 'Base64-encoded file content. Optional if text is provided.',
            },
            {
              name: 'filename',
              type: 'string',
              description: 'Optional source filename (used with file_data).',
            },
            {
              name: 'file_format',
              type: 'string',
              description: 'Optional source format (e.g., pdf, txt, json, md).',
            },
            {
              name: 'model',
              type: 'string',
              required: true,
              description: 'Provider/model key used for extraction.',
              possibleValues: ['ollama', 'claude'],
              defaultValue: 'ollama',
            },
            {
              name: 'output_type',
              type: 'string',
              required: true,
              description: 'Schema shape for output metadata.',
              possibleValues: ['pala', 'archipelago', 'combined'],
              defaultValue: 'pala',
            },
            {
              name: 'language',
              type: 'string',
              description: 'Optional language hint (ISO code).',
            },
            {
              name: 'document_context',
              type: 'string',
              description: 'Optional context hint for better extraction.',
            },
            {
              name: 'custom_prompt',
              type: 'string',
              description: 'Optional custom extraction prompt override.',
            },
            {
              name: 'schema_version',
              type: 'string',
              description: 'Optional output schema version tag.',
              defaultValue: '1.0.0',
            },
          ],
        },
      ],
    },
    {
      id: 'storage-agent',
      name: 'Storage Agent',
      tools: [
        {
          name: 'store_document',
          description: 'Store document with unified schema',
          placeholder: 'Enter JSON with type, original_file, file_format, processed_data, metadata, app_data, created_by',
          examples: [
            {
              label: 'OCR PDF document',
              input: '{"type": "ocr", "original_file": "document.pdf", "file_format": "pdf", "processed_data": {"text": "Extracted text content"}, "metadata": {"language": "en", "confidence": 0.94}, "app_data": {"project": "test"}, "created_by": "web-dashboard"}',
            },
            {
              label: 'Metadata extraction output',
              input: '{"type": "metadata", "original_file": "doc-123", "file_format": "json", "processed_data": {"document_type": "letter", "summary": "A short archival letter"}, "metadata": {"source": "metadata-extraction-agent"}, "app_data": {"pipeline": "enrichment"}, "created_by": "metadata-extraction-agent", "tags": {"domain": "archive", "lang": "en"}}',
            },
          ],
          schemaFields: [
            { name: 'type', type: 'string', required: true, description: 'Document category.' , possibleValues: ['ocr', 'transcription', 'metadata', 'translation', 'note']},
            { name: 'original_file', type: 'string', required: true, description: 'Original source file name/path.' },
            { name: 'file_format', type: 'string', required: true, description: 'File format or payload format.', possibleValues: ['pdf', 'txt', 'json', 'md', 'jpg', 'png'] },
            { name: 'processed_data', type: 'object|string', required: true, description: 'Primary content payload to store.' },
            { name: 'metadata', type: 'object', description: 'General metadata for indexing/filtering.' },
            { name: 'app_data', type: 'object', description: 'App/pipeline-specific metadata.' },
            { name: 'created_by', type: 'string', description: 'Producer identity for audit.', defaultValue: 'api' },
            { name: 'provider', type: 'string', description: 'Optional provider override.' },
            { name: 'backend', type: 'string', description: 'Optional backend override.' },
            { name: 'signature', type: 'string', description: 'Optional signature/checksum metadata.' },
            { name: 'tags', type: 'object', description: 'Optional key/value tags.' },
          ],
        },
        {
          name: 'retrieve_document',
          description: 'Retrieve document by ID with optional file content',
          placeholder: 'Enter JSON: {"document_id": "...", "include_original_file": false}',
          examples: [
            { label: 'Retrieve metadata only', input: '{"document_id": "doc-12345678"}' },
            { label: 'Retrieve with file content', input: '{"document_id": "doc-12345678", "include_original_file": true}' },
          ],
          schemaFields: [
            { name: 'document_id', type: 'string', required: true, description: 'Document identifier returned by store_document.' },
            { name: 'include_original_file', type: 'boolean', description: 'If true, returns original file as base64-encoded content. Default: false', defaultValue: 'false' },
          ],
        },
        {
          name: 'list_documents',
          description: 'List documents with filters',
          placeholder: 'Enter JSON: {"type": "...", "created_by": "...", "limit": 10, "offset": 0}',
          examples: [
            { label: 'Filter by type + creator', input: '{"type": "ocr", "created_by": "web-dashboard", "limit": 10, "offset": 0}' },
            { label: 'Paginated all docs', input: '{"limit": 25, "offset": 0}' },
          ],
          schemaFields: [
            { name: 'type', type: 'string', description: 'Filter by document type.' },
            { name: 'created_by', type: 'string', description: 'Filter by creator identity.' },
            { name: 'provider', type: 'string', description: 'Optional provider filter.' },
            { name: 'backend', type: 'string', description: 'Optional backend filter.' },
            { name: 'limit', type: 'number', description: 'Max number of records returned.', defaultValue: '100' },
            { name: 'offset', type: 'number', description: 'Pagination offset.', defaultValue: '0' },
          ],
        },
        {
          name: 'delete_document',
          description: 'Delete a single document',
          placeholder: 'Enter JSON: {"document_id": "..."}',
          examples: [
            { label: 'Delete one by id', input: '{"document_id": "doc-12345678"}' },
          ],
          schemaFields: [
            { name: 'document_id', type: 'string', required: true, description: 'Document identifier to delete.' },
          ],
        },
        {
          name: 'get_stats',
          description: 'Get storage statistics',
          placeholder: 'Enter JSON: {}',
          examples: [
            { label: 'Default', input: '{}' },
          ],
          schemaFields: [],
        },
        {
          name: 'delete_all_documents',
          description: 'Delete all documents (reset storage)',
          placeholder: 'Enter JSON: {}',
          examples: [
            { label: 'Dangerous reset', input: '{}' },
          ],
          schemaFields: [],
        },
        {
          name: 'answer_content_query',
          description: 'Search documents and answer query',
          placeholder: 'Enter JSON: {"query": "..."}',
          examples: [
            { label: 'Local search answer', input: '{"query": "find documents about invoices", "limit": 5}' },
            { label: 'Filter by provider', input: '{"query": "summarize Buddhist ethics mentions", "provider": "local-provider", "limit": 8, "include_web": false}' },
          ],
          schemaFields: [
            { name: 'query', type: 'string', required: true, description: 'Natural-language query over stored content.' },
            { name: 'limit', type: 'number', description: 'Max references to include in answer.', defaultValue: '5' },
            { name: 'provider', type: 'string', description: 'Optional provider filter.' },
            { name: 'backend', type: 'string', description: 'Optional backend filter.' },
            { name: 'include_web', type: 'boolean', description: 'Include separate web-section placeholder.', defaultValue: 'true' },
          ],
        },
        {
          name: 'semantic_search_documents',
          description: 'Semantic search across documents using embeddings',
          placeholder: 'Enter JSON: {"query": "..."}',
          examples: [
            { label: 'Buddhist teachings', input: '{"query": "What was said in bodhgaya", "limit": 5, "min_confidence": 0.5}' },
            { label: 'High confidence search', input: '{"query": "meditation techniques", "limit": 3, "min_confidence": 0.7, "include_original_content": true}' },
            { label: 'Low threshold search', input: '{"query": "any documents", "limit": 10, "min_confidence": 0.3}' },
          ],
          schemaFields: [
            { name: 'query', type: 'string', required: true, description: 'Search query text or question to find similar documents.' },
            { name: 'limit', type: 'number', description: 'Maximum number of documents to return.', defaultValue: '5' },
            { name: 'min_confidence', type: 'number', description: 'Minimum similarity score threshold (0-1).', defaultValue: '0.5' },
            { name: 'include_original_content', type: 'boolean', description: 'If true, includes original document content in results.', defaultValue: 'false' },
          ],
        },
      ],
    },
  ];

  const getFieldSampleValue = (field: ToolField): any => {
    if (field.defaultValue !== undefined) {
      if (field.type === 'number') {
        return Number(field.defaultValue);
      }
      if (field.type === 'boolean') {
        return field.defaultValue.toLowerCase() === 'true';
      }
      return field.defaultValue;
    }

    if (field.possibleValues?.length) {
      return field.possibleValues[0];
    }

    if (field.type.includes('number[]')) {
      return [1, 2, 3];
    }
    if (field.type.includes('number')) {
      return 1;
    }
    if (field.type.includes('boolean')) {
      return false;
    }
    if (field.type.includes('object')) {
      return { sample: true };
    }
    if (field.type.includes('string[]')) {
      return ['value1', 'value2'];
    }
    return `sample_${field.name}`;
  };

  const getFullSchemaArguments = (tool?: ToolDef): Record<string, any> => {
    if (!tool?.schemaFields?.length) {
      return {};
    }

    const args: Record<string, any> = {};
    for (const field of tool.schemaFields) {
      args[field.name] = getFieldSampleValue(field);
    }
    return args;
  };

  const getSelectedExampleInput = (tool?: ToolDef): string => {
    if (!tool) {
      return '{}';
    }

    if (selectedExampleIndex === 0) {
      return JSON.stringify(getFullSchemaArguments(tool), null, 2);
    }

    const preset = tool.examples[selectedExampleIndex - 1];
    return preset?.input || JSON.stringify(getFullSchemaArguments(tool), null, 2);
  };

  const invokeTool = async () => {
    if (!client) return;

    try {
      setLoading(true);
      setResult(null);

      // Parse JSON input
      let params: any = {};
      try {
        params = JSON.parse(input);
      } catch (e) {
        setResult(`Error: Invalid JSON input - ${e}`);
        setLoading(false);
        return;
      }

      // If store_document and file selected, always inject file data
      if (selectedTool === 'store_document' && selectedFile && fileBase64) {
        params.original_file_data = fileBase64;
        params.original_file = selectedFile.name;
        params.original_file_mime = selectedFile.type || '';
      }

      const request = {
        jsonrpc: '2.0',
        method: 'tools/invoke',
        params: {
          agentId: selectedAgent,
          toolName: selectedTool,
          arguments: params,
        },
        id: `invoke-${Date.now()}`,
      };

      client.send(JSON.stringify(request));

      const handleMessage = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.id === request.id) {
            setResult(response.result || response.error);
            client.removeEventListener('message', handleMessage);
            setLoading(false);
          }
        } catch (e) {
          console.error('Failed to parse response:', e);
        }
      };

      client.addEventListener('message', handleMessage);
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : 'Failed to invoke tool' });
      setLoading(false);
    }
  };

  const currentAgent = AGENTS.find((a) => a.id === selectedAgent);
  const currentTool = currentAgent?.tools.find((t) => t.name === selectedTool);

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Main Area: Tools (Left) + Results (Right/Center) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Left Panel: Tool List (1 column) */}
        <div className="lg:col-span-1 overflow-y-auto">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 sticky top-0">
            <h2 className="text-lg font-semibold text-white mb-4">Available Tools</h2>

            {/* Agent Selector */}
            <div className="space-y-2">
              {AGENTS.map((agent) => (
                <div key={agent.id} className="space-y-2">
                  <button
                    onClick={() => {
                      setSelectedAgent(agent.id);
                      setSelectedTool(agent.tools[0].name);
                      setSelectedExampleIndex(0);
                      setInput('');
                      setResult(null);
                    }}
                    className={`w-full px-4 py-2 rounded-lg text-left font-medium transition-colors ${
                      selectedAgent === agent.id
                        ? 'bg-blue-900 text-blue-100'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {agent.name}
                  </button>

                  {selectedAgent === agent.id && (
                    <div className="ml-4 space-y-1">
                      {agent.tools.map((tool) => (
                        <button
                          key={tool.name}
                          onClick={() => {
                            setSelectedTool(tool.name);
                            setSelectedExampleIndex(0);
                            setInput('');
                            setResult(null);
                          }}
                          className={`w-full px-3 py-2 rounded text-left text-sm transition-colors ${
                            selectedTool === tool.name
                              ? 'bg-slate-600 text-white'
                              : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                          }`}
                        >
                          <div className="font-mono text-xs">{tool.name}</div>
                          <div className="text-xs opacity-75">{tool.description}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel: Input & Invoke (2 columns) */}
        <div className="lg:col-span-2 space-y-6 overflow-y-auto min-h-0">
          {/* Invoke Panel */}
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-md font-semibold text-white">Test Tool: <span className="font-mono text-blue-300">{selectedTool}</span></h3>
              {currentTool?.examples?.length ? (
                <div className="flex items-center gap-2">
                  <select
                    value={selectedExampleIndex}
                    onChange={(e) => setSelectedExampleIndex(Number(e.target.value))}
                    className="text-xs px-2 py-1 bg-slate-700 border border-slate-600 text-slate-300 rounded"
                  >
                    <option value={0}>Full Schema</option>
                    {currentTool.examples.map((example, index) => (
                      <option key={example.label} value={index + 1}>
                        {example.label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => {
                      setInput(getSelectedExampleInput(currentTool));
                    }}
                    className="text-xs px-3 py-1 bg-blue-700 text-white rounded hover:bg-blue-600"
                  >
                    Use Example
                  </button>
                </div>
              ) : null}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Input Parameters</label>
              {/* File picker for tools that support file upload */}
              {(currentTool?.name === 'store_document' ||
                currentTool?.name === 'process_and_store_document' ||
                currentTool?.name === 'extract_metadata') && (
                <div className="mb-2 flex flex-col gap-2">
                  <input
                    type="file"
                    accept="*"
                    onChange={handleFileChange}
                    className="px-2 py-1 text-xs bg-slate-700 text-slate-200 rounded border border-slate-600"
                  />
                  {selectedFile && (
                    <div className="text-xs text-slate-400">
                      Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>
              )}

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={currentTool?.placeholder || 'Enter input...'}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-100 text-sm font-mono placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={8}
              />
            </div>

            <button
              onClick={invokeTool}
              disabled={loading || (!input && selectedTool !== 'tool_list_content')}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Invoking...' : 'Invoke Tool'}
            </button>
          </div>

          {/* Results Panel */}
          {result && (
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <label className="block text-sm font-medium text-slate-300 mb-2">Result</label>
              <pre className="bg-slate-900 p-3 rounded-lg text-xs overflow-x-auto text-green-400 border border-slate-600 max-h-64">
                {JSON.stringify(result, null, 2)}
              </pre>
              {/* Download button if result contains file data */}
              {(() => {
                const docs = Array.isArray(result) ? result : [result];
                return docs.map((doc, idx) => {
                  if (doc && doc.original_file_data && doc.original_file) {
                    const handleDownload = () => {
                      const byteCharacters = atob(doc.original_file_data);
                      const byteNumbers = new Array(byteCharacters.length);
                      for (let i = 0; i < byteCharacters.length; i++) {
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                      }
                      const byteArray = new Uint8Array(byteNumbers);
                      const blob = new Blob([byteArray], { type: doc.original_file_mime || 'application/octet-stream' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = doc.original_file;
                      document.body.appendChild(a);
                      a.click();
                      setTimeout(() => {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                      }, 100);
                    };
                    return (
                      <button
                        key={doc.original_file + idx}
                        onClick={handleDownload}
                        className="mt-2 px-3 py-1 bg-blue-700 text-white rounded text-xs hover:bg-blue-800"
                      >
                        Download {doc.original_file}
                      </button>
                    );
                  }
                  return null;
                });
              })()}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Panel: Expandable Integration Guide */}
      <div className="border-t border-slate-700 pt-6">
        <button
          onClick={() => setExpandedGuide(!expandedGuide)}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-750 rounded-lg border border-slate-700 text-white font-medium transition-colors"
        >
          <span className={`transform transition-transform ${expandedGuide ? 'rotate-180' : ''}`}>▼</span>
          Integration Guide & Tool Schema
        </button>

        {expandedGuide && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            {/* Integration Guide */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h3 className="text-md font-semibold text-white mb-3">How to Integrate</h3>
              <div className="space-y-3 text-sm text-slate-300">
                <div>
                  <p className="font-medium text-slate-200 mb-1">1. Connect to MCP Server</p>
                  <pre className="bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600 overflow-x-auto">
{`const ws = new WebSocket('ws://localhost:3010');`}
                  </pre>
                </div>

                <div>
                  <p className="font-medium text-slate-200 mb-1">2. Send JSON-RPC Request</p>
                  <pre className="bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600 overflow-x-auto">
{`ws.send(JSON.stringify({
  jsonrpc: "2.0",
  method: "tools/invoke",
  params: {
    name: "${selectedTool}",
    arguments: ${input || '{}'}
  },
  id: "req-1"
}));`}
                  </pre>
                </div>

                <div>
                  <p className="font-medium text-slate-200 mb-1">3. Listen for Response</p>
                  <pre className="bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600 overflow-x-auto">
{`ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.result);
};`}
                  </pre>
                </div>
              </div>
            </div>

            {/* Tool Schema */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h3 className="text-md font-semibold text-white mb-3">
                Schema: <span className="font-mono text-blue-300">{selectedTool}</span>
              </h3>
              <div className="text-xs space-y-3 text-slate-300 max-h-96 overflow-y-auto">
                {currentTool?.schemaFields?.length ? (
                  <div>
                    <p className="font-medium text-slate-200 mb-2">Input Parameters:</p>
                    <div className="text-slate-400 space-y-2">
                      {currentTool.schemaFields.map((field) => (
                        <div key={field.name} className="bg-slate-900 border border-slate-700 rounded p-2">
                          <div className="flex items-center gap-2">
                            <code className="text-blue-300 font-mono">{field.name}</code>
                            <span className="text-slate-500">: {field.type}</span>
                            {field.required ? (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900 text-red-200">required</span>
                            ) : (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">optional</span>
                            )}
                          </div>
                          <div className="text-slate-400 mt-1 text-xs">{field.description}</div>
                          {field.possibleValues?.length ? (
                            <div className="mt-1 text-slate-500 text-xs">
                              Values: {field.possibleValues.map((v) => `"${v}"`).join(', ')}
                            </div>
                          ) : null}
                          {field.defaultValue ? (
                            <div className="mt-1 text-slate-500 text-xs">Default: {field.defaultValue}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-slate-400">No input parameters required.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}



// Chat Panel - Chat with documents using RAG
function ChatPanel({ onOpenStorageExplorer }: { onOpenStorageExplorer: () => void }) {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: any[]; refinedQuery?: string; queryRefinement?: any }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [showRawPreviewJson, setShowRawPreviewJson] = useState(false);
  const [pinnedSources, setPinnedSources] = useState<any[]>([]);
  const previewPanelRef = useRef<HTMLDivElement | null>(null);
  const { send } = useWebSocket();

  const unwrapToolResult = (payload: any) => {
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

  const openSourcePreview = async (documentId: string) => {
    if (!documentId) return;
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewDocument(null);
    setShowRawPreviewJson(false);

    try {
      // Retrieve document plus original file so the preview can render inline
      const response: any = await send('tools/invoke', {
        agentId: 'storage-agent',
        name: 'retrieve_document',
        arguments: {
          document_id: documentId,
          include_original_file: true,
        },
      });

      const data = unwrapToolResult(response);
      const payload = data?.document_id ? data : data?.result || data || {};
      if (payload?.document_id) {
        // Keep preview document metadata; UI will show matched_text when available
        setPreviewDocument(payload);
        requestAnimationFrame(() => {
          previewPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      } else {
        setPreviewError('Could not load document preview.');
      }
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : 'Failed to load preview');
    } finally {
      setPreviewLoading(false);
    }
  };

  const openFullDocument = async (documentId: string) => {
    if (!documentId) return;
    try {
      setPreviewLoading(true);
      const response: any = await send('tools/invoke', {
        agentId: 'storage-agent',
        name: 'retrieve_document',
        arguments: {
          document_id: documentId,
          include_original_file: true,
        },
      });

      const data = unwrapToolResult(response);
      const payload = data?.document_id ? data : data?.result || data || {};
      const b64 = payload?.original_file_data;
      const mime = payload?.file_format ? (payload.file_format === 'pdf' ? 'application/pdf' : 'application/octet-stream') : 'application/octet-stream';
      if (b64) {
        // Convert base64 to blob and open in new tab
        const byteChars = atob(b64);
        const byteNumbers = new Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) {
          byteNumbers[i] = byteChars.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: mime });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        setPreviewError('Original file not available for download.');
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Failed to open document');
    } finally {
      setPreviewLoading(false);
    }
  };

  const getPreviewText = (doc: any) => {
    if (!doc) return '';
    return (
      doc.matched_text ||
      doc.ocr_text ||
      doc.processed_data?.text ||
      doc.processed_data?.content ||
      doc.enriched_metadata?.content?.summary ||
      doc.summary ||
      ''
    );
  };

  const getPreviewMimeType = (doc: any) => {
    if (!doc) return '';
    if (doc.original_file_mime) return doc.original_file_mime;
    if (doc.file_format === 'pdf') return 'application/pdf';
    if (doc.file_format === 'json') return 'application/json';
    if (doc.file_format === 'md') return 'text/markdown';
    if (doc.file_format === 'txt') return 'text/plain';
    return '';
  };

  const decodeBase64ToText = (base64Value: string) => {
    try {
      return atob(base64Value);
    } catch {
      return '';
    }
  };

  const getInlinePreview = (doc: any) => {
    if (!doc) return null;

    const mimeType = getPreviewMimeType(doc);
    const base64Value = doc.original_file_data;
    const previewText = getPreviewText(doc);

    if (base64Value && mimeType === 'application/pdf') {
      return (
        <iframe
          title={`Preview ${doc.original_file || doc.document_id}`}
          src={`data:application/pdf;base64,${base64Value}`}
          className="w-full h-[28rem] rounded border border-slate-700 bg-slate-950"
        />
      );
    }

    if (base64Value && (mimeType.startsWith('text/') || mimeType === 'application/json' || doc.file_format === 'json')) {
      const textContent = decodeBase64ToText(base64Value);
      return (
        <pre className="whitespace-pre-wrap break-words bg-slate-950 border border-slate-700 rounded p-4 text-sm text-slate-200 max-h-[28rem] overflow-auto">
          {textContent || previewText || 'No text preview available.'}
        </pre>
      );
    }

    if (base64Value && (mimeType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes((doc.file_format || '').toLowerCase()))) {
      return (
        <img
          src={`data:${mimeType || 'image/*'};base64,${base64Value}`}
          alt={doc.original_file || doc.document_id}
          className="max-w-full max-h-[28rem] rounded border border-slate-700 bg-slate-950 object-contain"
        />
      );
    }

    return (
      <div className="rounded border border-slate-700 bg-slate-950 p-4 text-sm text-slate-300">
        {previewText ? <p className="whitespace-pre-wrap">{previewText}</p> : <p>No inline preview available for this file type.</p>}
      </div>
    );
  };

  const getSourcePreviewText = (source: any) => {
    return source?.matched_text || source?.excerpt || source?.summary || source?.preview_text || '';
  };

  const getFriendlyMatchLabel = (matchedPath?: string) => {
    if (!matchedPath) return '';
    const normalized = matchedPath.toLowerCase();
    if (normalized.includes('metadata')) return 'metadata';
    if (normalized.includes('summary')) return 'summary';
    if (normalized.includes('processed_data') || normalized.includes('ocr_text') || normalized.includes('content') || normalized.includes('text')) {
      return 'document text';
    }
    if (normalized.includes('filename') || normalized.includes('file')) return 'filename';
    return 'matched field';
  };

  const getAssistantHeadline = (msg: { content: string; sources?: any[] }) => {
    if (msg.sources && msg.sources.length > 0) {
      return `Found ${msg.sources.length} matching document${msg.sources.length === 1 ? '' : 's'}.`;
    }
    return msg.content;
  };

  const copySourceSnippet = async (source: any) => {
    const text = getSourcePreviewText(source);
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore clipboard failures in unsupported contexts
    }
  };

  const togglePinnedSource = (source: any) => {
    if (!source?.document_id) return;
    setPinnedSources((current) => {
      const exists = current.some((item) => item.document_id === source.document_id);
      if (exists) {
        return current.filter((item) => item.document_id !== source.document_id);
      }
      if (current.length >= 3) {
        return [...current.slice(1), source];
      }
      return [...current, source];
    });
  };

  const isPinnedSource = (documentId: string) => pinnedSources.some((item) => item.document_id === documentId);

  const clearPinnedSources = () => setPinnedSources([]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setPreviewDocument(null);
    setPreviewError(null);
    setShowRawPreviewJson(false);
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const result: any = await send('tools/invoke', {
        agentId: 'chat-agent',
        name: 'chat_with_documents',
        arguments: {
          query: userMessage,
          include_original_content: false,
        }
      });

      const data = unwrapToolResult(result);
      const documents = Array.isArray(data?.source_documents) ? data.source_documents : [];
      
      // Build response message
      const content = data?.answer || 'No documents found matching your query.';

      const assistantMessage = {
        role: 'assistant' as const,
        content: content,
        sources: documents,
        refinedQuery: data?.refined_query,
        queryRefinement: data?.query_refinement,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant' as const,
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        sources: []
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-bold text-white mb-4">Chat with Documents</h2>
        <p className="text-sm text-slate-400 mb-4">
          Retrieval-first mode: the chat returns matched documents and excerpts, not free-form answers.
        </p>

        {/* Chat Messages */}
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_24rem] gap-4 items-start">
          <div className="bg-slate-900 rounded h-96 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-slate-500 text-center pt-12">
                <p>Start a conversation by asking a question about your documents.</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-100'
                    }`}
                  >
                    <p className="text-sm">
                      {msg.role === 'assistant' ? getAssistantHeadline(msg) : msg.content}
                    </p>

                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <p className="text-xs text-slate-400 mt-2">Open a source to inspect the exact hit location.</p>
                    )}

                    {msg.role === 'assistant' && (msg.refinedQuery || msg.queryRefinement || msg.content) && (
                      <details className="mt-2 text-xs text-slate-300">
                        <summary className="cursor-pointer text-slate-400">Details</summary>
                        <div className="mt-2 space-y-2">
                          {msg.refinedQuery && <p>Refined query: {msg.refinedQuery}</p>}
                          {msg.queryRefinement?.search_method && <p>Search method: {msg.queryRefinement.search_method}</p>}
                          <p className="whitespace-pre-wrap text-slate-300">{msg.content}</p>
                        </div>
                      </details>
                    )}

                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-600 text-xs">
                        <p className="font-semibold mb-2">📄 Sources:</p>
                        <div className="space-y-1">
                          {msg.sources.map((source: any, sidx: number) => (
                            <div
                              key={sidx}
                              onClick={() => openSourcePreview(source.document_id)}
                              className="w-full cursor-pointer text-left bg-slate-600 bg-opacity-50 rounded p-3 hover:bg-slate-500 transition-colors"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="font-medium text-slate-200 break-words">{source.filename || 'Matched document'}</p>
                                </div>
                                {isPinnedSource(source.document_id) && (
                                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-900 text-amber-100">Pinned</span>
                                )}
                              </div>

                              {getSourcePreviewText(source) && (
                                <p className="text-slate-400 mt-2 line-clamp-2">{getSourcePreviewText(source)}</p>
                              )}

                                <details className="mt-2 text-[10px] text-slate-300">
                                  <summary className="cursor-pointer text-slate-400">Details</summary>
                                  <div className="mt-2 flex flex-wrap gap-2">
                                    <span className="px-2 py-0.5 rounded-full bg-blue-900 text-blue-100">
                                      {Math.round((source.relevance_score || 0) * 100)}%
                                    </span>
                                    {source.matched_path && (
                                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-200">
                                        {getFriendlyMatchLabel(source.matched_path)}
                                      </span>
                                    )}
                                    {source.match_method && (
                                      <span className="px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-100">
                                        {source.match_method}
                                      </span>
                                    )}
                                  </div>
                                </details>

                              <div className="mt-3 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openSourcePreview(source.document_id);
                                  }}
                                  className="px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                                >
                                  Jump to hit
                                </button>
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    copySourceSnippet(source);
                                  }}
                                  className="px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                                >
                                  Copy snippet
                                </button>
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    togglePinnedSource(source);
                                  }}
                                  className="px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                                >
                                  {isPinnedSource(source.document_id) ? 'Unpin' : 'Pin compare'}
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg">
                  <p className="text-sm">Thinking...</p>
                </div>
              </div>
            )}
          </div>

          <aside className="space-y-4 lg:sticky lg:top-4">
            {previewDocument ? (
              <div ref={previewPanelRef} className="rounded-lg border border-slate-700 bg-slate-900 p-4">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-white font-semibold">Document Preview</h3>
                    <p className="text-xs text-slate-400 break-words">{previewDocument.original_file || previewDocument.document_id}</p>
                    {previewDocument.matched_path && (
                      <p className="text-[10px] text-slate-500 mt-1">Matched in: {getFriendlyMatchLabel(previewDocument.matched_path)}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 justify-end">
                    <button
                      type="button"
                      onClick={() => openFullDocument(previewDocument.document_id)}
                      className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                    >
                      Open Full
                    </button>
                    <button
                      type="button"
                      onClick={() => onOpenStorageExplorer()}
                      className="text-xs px-2 py-1 rounded bg-slate-600 text-slate-200 hover:bg-slate-500"
                    >
                      Explorer
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPreviewDocument(null);
                        setPreviewError(null);
                      }}
                      className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                    >
                      Close
                    </button>
                  </div>
                </div>

                <div className="space-y-4 text-sm text-slate-200">
                  {getInlinePreview(previewDocument)}

                  <div className="rounded border border-slate-700 bg-slate-950">
                    <button
                      type="button"
                      onClick={() => setShowRawPreviewJson((prev) => !prev)}
                      className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-900"
                    >
                      <span>Raw JSON details</span>
                      <span>{showRawPreviewJson ? 'Hide' : 'Show'}</span>
                    </button>
                    {showRawPreviewJson && (
                      <pre className="max-h-64 overflow-x-auto border-t border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
{JSON.stringify(previewDocument, null, 2)}
                      </pre>
                    )}
                  </div>

                  {pinnedSources.length > 0 && (
                    <div className="rounded border border-slate-700 bg-slate-950 p-3">
                      <div className="flex items-center justify-between gap-2 mb-3">
                        <h4 className="text-xs font-semibold text-slate-200">Compare pinned results</h4>
                        <button
                          type="button"
                          onClick={clearPinnedSources}
                          className="text-[10px] px-2 py-1 rounded bg-slate-700 text-slate-200 hover:bg-slate-600"
                        >
                          Clear
                        </button>
                      </div>
                      <div className="space-y-2">
                        {pinnedSources.slice(0, 3).map((source: any) => (
                          <div key={source.document_id} className="rounded border border-slate-700 bg-slate-900 p-2 text-xs">
                            <div className="flex items-start justify-between gap-2">
                              <p className="font-medium text-slate-200 break-words">{source.filename || 'Matched document'}</p>
                              <button
                                type="button"
                                onClick={() => openSourcePreview(source.document_id)}
                                className="text-[10px] px-2 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600"
                              >
                                Open
                              </button>
                            </div>
                            <div className="mt-1 flex flex-wrap gap-2 text-[10px]">
                              <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-200">Pinned result</span>
                            </div>
                            {getSourcePreviewText(source) && (
                              <p className="mt-2 text-slate-400 line-clamp-3">{getSourcePreviewText(source)}</p>
                            )}
                            <details className="mt-2 text-[10px] text-slate-300">
                              <summary className="cursor-pointer text-slate-400">Details</summary>
                              <div className="mt-2 flex flex-wrap gap-2">
                                <span className="px-2 py-0.5 rounded-full bg-blue-900 text-blue-100">
                                  {(source.relevance_score * 100).toFixed(0)}%
                                </span>
                                {source.matched_path && (
                                  <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-200">{getFriendlyMatchLabel(source.matched_path)}</span>
                                )}
                              </div>
                            </details>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
                No preview selected.
              </div>
            )}

            {previewLoading && (
              <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
                Loading document preview...
              </div>
            )}

            {previewError && (
              <div className="rounded-lg border border-red-700 bg-red-950 p-4 text-sm text-red-200">
                {previewError}
              </div>
            )}
          </aside>
        </div>

        {previewLoading && (
          <div className="mt-4 rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
            Loading document preview...
          </div>
        )}

        {previewError && (
          <div className="mt-4 rounded-lg border border-red-700 bg-red-950 p-4 text-sm text-red-200">
            {previewError}
          </div>
        )}

        {/* Input Area */}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
            placeholder="Ask a question about your documents..."
            disabled={loading}
            className="flex-1 bg-slate-700 border border-slate-600 rounded px-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Storage Explorer - Browse and interact with stored content
function StorageExplorer() {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <ContentBrowser />
    </div>
  );
}
