'use client';

import { useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ContentBrowser } from './ContentBrowser';
import Browse from './Browse';

type Tab = 'browse' | 'storage' | 'developer';

export function PalaWebDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('browse');
  const { connected, send } = useWebSocket();

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-gray-50 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Pala Platform</h1>
                <p className="text-xs text-gray-500">Unified Storage & Services Layer</p>
              </div>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}
            >
              {connected ? '● Connected' : '● Disconnected'}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex gap-1 border-b border-gray-200">
            {/* Explore moved into Browse. Default entry point is Browse. */}
            <button
              onClick={() => setActiveTab('developer')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'developer'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Developer
            </button>
            <button
              onClick={() => setActiveTab('browse')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'browse'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Browse
            </button>
            <button
              onClick={() => setActiveTab('storage')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'storage'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Storage Explorer
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'browse' && (
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <Browse
              send={send}
              className="min-h-[60vh]"
              onOpenDocument={(documentId) => {
                if (typeof window === 'undefined' || !documentId) return;
                const url = new URL(`/document/${encodeURIComponent(documentId)}`, window.location.origin);
                window.open(url.toString(), '_blank', 'noopener,noreferrer');
              }}
            />
          </div>
        )}
        {activeTab === 'developer' && <DeveloperPanel />}
        {activeTab === 'storage' && <StorageExplorer />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-xs text-gray-500">
          <p>Pala Platform · {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}

// Developer Panel - Interactive tool testing with code examples
function DeveloperPanel() {
  const [expandedGuide, setExpandedGuide] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<string>('');

  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const arrayBuffer = reader.result as ArrayBuffer;
          const bytes = new Uint8Array(arrayBuffer);
          let binary = '';
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          resolve(btoa(binary));
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
      reader.readAsArrayBuffer(file);
    });

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setSelectedFiles(files);
    setUploadProgress('');

    if (files.length === 0) {
      setInput('');
      setResult(null);
      setUploadProgress('');
      return;
    }

    if (files.length === 1) {
      const file = files[0];
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      setInput(
        JSON.stringify(
          {
            original_file_name: file.name,
            file_format: ['pdf', 'txt', 'json', 'md', 'jpg', 'png'].includes(ext) ? ext : 'bin',
            document_type: 'ocr',
            created_by: 'web-dashboard',
          },
          null,
          2,
        ),
      );
      setUploadProgress('1/1 selected');
      return;
    }

    setInput(
      JSON.stringify(
        {
          documents: files.map((file) => ({
            original_file_name: file.name,
            file_size: file.size,
            file_type: file.type,
          })),
        },
        null,
        2,
      ),
    );
      setUploadProgress(`${files.length}/${files.length} selected`);
  };
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
        {
          name: 'get_document_questions',
          description: 'Get pre-generated questions for a document',
          placeholder: 'Enter JSON: {"document_id": "..."}',
          examples: [
            { label: 'Get questions for document', input: '{"document_id": "doc-12345678"}' },
          ],
          schemaFields: [
            { name: 'document_id', type: 'string', required: true, description: 'Document identifier to get questions for.' },
          ],
        },
        {
          name: 'search_questions',
          description: 'Search for similar pre-generated questions using vector similarity',
          placeholder: 'Enter JSON: {"query": "..."}',
          examples: [
            { label: 'Find related questions', input: '{"query": "Buddhist meditation practices", "limit": 5, "similarity_threshold": 0.5}' },
            { label: 'Broader search', input: '{"query": "what is Buddhism", "limit": 10, "similarity_threshold": 0.3}' },
          ],
          schemaFields: [
            { name: 'query', type: 'string', required: true, description: 'Search query to find similar questions.' },
            { name: 'limit', type: 'number', description: 'Maximum number of questions to return.', defaultValue: '5' },
            { name: 'similarity_threshold', type: 'number', description: 'Minimum similarity score (0-1).', defaultValue: '0.5' },
          ],
        },
        {
          name: 'regenerate_document_questions',
          description: 'Regenerate questions for a document (after metadata updates)',
          placeholder: 'Enter JSON: {"document_id": "..."}',
          examples: [
            { label: 'Regenerate questions', input: '{"document_id": "doc-12345678"}' },
          ],
          schemaFields: [
            { name: 'document_id', type: 'string', required: true, description: 'Document identifier to regenerate questions for.' },
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

      const invokeJsonRpc = (toolName: string, args: Record<string, any>) =>
        new Promise<any>((resolve, reject) => {
          const requestId = `invoke-${Date.now()}-${Math.random().toString(16).slice(2)}`;
          const request = {
            jsonrpc: '2.0',
            method: 'tools/invoke',
            params: {
              agentId: selectedAgent,
              toolName,
              arguments: args,
            },
            id: requestId,
          };

          const handleMessage = (event: MessageEvent) => {
            try {
              const response = JSON.parse(event.data);
              if (response.id !== requestId) {
                return;
              }

              client.removeEventListener('message', handleMessage);

              if (response.error) {
                reject(new Error(response.error.message || 'Failed to invoke tool'));
                return;
              }

              resolve(response.result || {});
            } catch (error) {
              client.removeEventListener('message', handleMessage);
              reject(error);
            }
          };

          client.addEventListener('message', handleMessage);
          client.send(JSON.stringify(request));
        });

      if (selectedTool === 'process_and_store_document' && selectedFiles.length > 0) {
        setUploadProgress(`0/${selectedFiles.length} invoked`);
        let baseParams: Record<string, any> = {};
        if (input.trim()) {
          try {
            baseParams = JSON.parse(input);
          } catch (e) {
            setUploadProgress('');
            setResult(`Error: Invalid JSON input - ${e}`);
            setLoading(false);
            return;
          }
        }

        const results: Array<{ file: string; result: any }> = [];
        for (let index = 0; index < selectedFiles.length; index++) {
          const file = selectedFiles[index];
          const fileBase64 = await fileToBase64(file);
          const ext = file.name.split('.').pop()?.toLowerCase() || '';
          const params = {
            ...baseParams,
            original_file: fileBase64,
            original_file_name: file.name,
            file_format: ['pdf', 'txt', 'json', 'md', 'jpg', 'png'].includes(ext) ? ext : 'bin',
            document_type: 'ocr',
            created_by: 'web-dashboard',
          };

          setUploadProgress(`${index + 1}/${selectedFiles.length} invoked`);
          const response = await invokeJsonRpc('process_and_store_document', params);
          results.push({ file: file.name, result: response });
          setUploadProgress(`${index + 1}/${selectedFiles.length} completed`);
        }

        setUploadProgress(`${selectedFiles.length}/${selectedFiles.length} completed`);
        setResult(results);
        setLoading(false);
        return;
      }

      // Parse JSON input
      let params: any = {};
      try {
        params = JSON.parse(input);
      } catch (e) {
        setUploadProgress('');
        setResult(`Error: Invalid JSON input - ${e}`);
        setLoading(false);
        return;
      }

      const response = await invokeJsonRpc(selectedTool, params);
      setUploadProgress('');
      setResult(response);
      setLoading(false);
    } catch (err) {
      setUploadProgress('');
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
          <div className="bg-gray-100 rounded-lg p-6 border border-gray-300 sticky top-0">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Tools</h2>

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
                        ? 'bg-blue-100 text-blue-900'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
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
                              ? 'bg-gray-300 text-gray-900'
                              : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
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
          <div className="bg-gray-100 rounded-lg p-6 border border-gray-300 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-md font-semibold text-gray-900">Test Tool: <span className="font-mono text-blue-600">{selectedTool}</span></h3>
              {currentTool?.examples?.length ? (
                <div className="flex items-center gap-2">
                  <select
                    value={selectedExampleIndex}
                    onChange={(e) => setSelectedExampleIndex(Number(e.target.value))}
                    className="text-xs px-2 py-1 bg-gray-200 border border-gray-300 text-gray-900 rounded"
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
              <label className="block text-sm font-medium text-gray-700 mb-2">Input Parameters</label>
              {/* File picker for tools that support file upload */}
              {(currentTool?.name === 'store_document' ||
                currentTool?.name === 'process_and_store_document' ||
                currentTool?.name === 'extract_metadata') && (
                <div className="mb-2 flex flex-col gap-2">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileInputChange}
                    className="px-2 py-1 text-xs bg-gray-200 text-gray-900 rounded border border-gray-300"
                  />
                  {selectedFiles.length > 0 && (
                    <div className="text-xs text-gray-600 space-y-1">
                      {selectedFiles.map((file) => (
                        <div key={`${file.name}-${file.size}`}>Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)</div>
                      ))}
                    </div>
                  )}
                  {uploadProgress && (
                    <div className="text-xs font-medium text-blue-600 bg-blue-50 border border-blue-300 rounded px-3 py-2">
                      {uploadProgress}
                    </div>
                  )}
                </div>
              )}

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={currentTool?.placeholder || 'Enter input...'}
                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm font-mono placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={8}
              />
            </div>

            <button
              onClick={invokeTool}
              disabled={
                loading ||
                ((!input && selectedTool !== 'tool_list_content') &&
                  !(selectedTool === 'process_and_store_document' && selectedFiles.length > 0))
              }
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Invoking...' : 'Invoke Tool'}
            </button>
          </div>

          {/* Results Panel */}
          {result && (
            <div className="bg-gray-100 rounded-lg p-6 border border-gray-300">
              <label className="block text-sm font-medium text-gray-700 mb-2">Result</label>
              <pre className="bg-white p-3 rounded-lg text-xs overflow-x-auto text-green-700 border border-gray-300 max-h-64">
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
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
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
      <div className="border-t border-gray-300 pt-6">
        <button
          onClick={() => setExpandedGuide(!expandedGuide)}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg border border-gray-300 text-gray-900 font-medium transition-colors"
        >
          <span className={`transform transition-transform ${expandedGuide ? 'rotate-180' : ''}`}>▼</span>
          Integration Guide & Tool Schema
        </button>

        {expandedGuide && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            {/* Integration Guide */}
            <div className="bg-gray-100 rounded-lg p-6 border border-gray-300">
              <h3 className="text-md font-semibold text-gray-900 mb-3">How to Integrate</h3>
              <div className="space-y-3 text-sm text-gray-700">
                <div>
                  <p className="font-medium text-gray-800 mb-1">1. Connect to MCP Server</p>
                  <pre className="bg-white p-2 rounded text-xs text-blue-600 border border-gray-300 overflow-x-auto">
{`const ws = new WebSocket('ws://localhost:3010');`}
                  </pre>
                </div>

                <div>
                  <p className="font-medium text-gray-800 mb-1">2. Send JSON-RPC Request</p>
                  <pre className="bg-white p-2 rounded text-xs text-blue-600 border border-gray-300 overflow-x-auto">
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
                  <p className="font-medium text-gray-800 mb-1">3. Listen for Response</p>
                  <pre className="bg-white p-2 rounded text-xs text-blue-600 border border-gray-300 overflow-x-auto">
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
              <div className="text-xs space-y-3 text-gray-700 max-h-96 overflow-y-auto">
                {currentTool?.schemaFields?.length ? (
                  <div>
                    <p className="font-medium text-gray-800 mb-2">Input Parameters:</p>
                    <div className="text-gray-600 space-y-2">
                      {currentTool.schemaFields.map((field) => (
                        <div key={field.name} className="bg-gray-100 border border-gray-300 rounded p-2">
                          <div className="flex items-center gap-2">
                            <code className="text-blue-600 font-mono">{field.name}</code>
                            <span className="text-gray-500">: {field.type}</span>
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



// ChatPanel removed

// Storage Explorer - Browse and interact with stored content
function StorageExplorer() {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <ContentBrowser />
    </div>
  );
}
