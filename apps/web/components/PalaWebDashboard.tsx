'use client';

import { useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ContentBrowser } from './ContentBrowser';

type Tab = 'storage' | 'developer';

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
  const [selectedAgent, setSelectedAgent] = useState<string>('sample-agent');
  const [selectedTool, setSelectedTool] = useState<string>('echo');
  const [input, setInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { client } = useWebSocket();

  const AGENTS = [
    {
      id: 'sample-agent',
      name: 'Sample Agent',
      tools: [
        { 
          name: 'echo', 
          description: 'Echo back input text', 
          placeholder: 'Enter JSON: {"text": "Hello World"}',
          exampleInput: '{"text": "Hello World"}'
        },
        { 
          name: 'sum', 
          description: 'Sum array of numbers', 
          placeholder: 'Enter JSON: {"numbers": [1, 2, 3]}',
          exampleInput: '{"numbers": [1, 2, 3, 4, 5]}'
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
          placeholder: 'Enter JSON with text, model, output_type',
          exampleInput: '{"text": "Dear Dr. Smith,\\n\\nI am writing to you regarding the upcoming conference on Digital Humanities to be held in New Delhi on March 15, 2024.\\n\\nAs discussed in our previous meeting, I would like to present our research on using AI for manuscript analysis.\\n\\nBest regards,\\nProf. Kumar", "model": "ollama", "output_type": "pala"}'
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
          exampleInput: '{"type": "ocr", "original_file": "document.pdf", "file_format": "pdf", "processed_data": {"text": "Extracted text content"}, "metadata": {"language": "en"}, "app_data": {"project": "test"}, "created_by": "web-dashboard"}'
        },
        {
          name: 'retrieve_document',
          description: 'Retrieve document by ID',
          placeholder: 'Enter JSON: {"document_id": "..."}',
          exampleInput: '{"document_id": "doc-12345678"}'
        },
        {
          name: 'list_documents',
          description: 'List documents with filters',
          placeholder: 'Enter JSON: {"type": "...", "limit": 10, "offset": 0}',
          exampleInput: '{"type": "ocr", "limit": 10, "offset": 0}'
        },
        {
          name: 'get_stats',
          description: 'Get storage statistics',
          placeholder: 'Enter JSON: {}',
          exampleInput: '{}'
        },
        {
          name: 'delete_all_documents',
          description: 'Delete all documents (reset storage)',
          placeholder: 'Enter JSON: {}',
          exampleInput: '{}'
        },
        {
          name: 'answer_content_query',
          description: 'Search documents and answer query',
          placeholder: 'Enter JSON: {"query": "..."}',
          exampleInput: '{"query": "find documents about invoices", "limit": 5}'
        },
      ],
    },
  ];

  const getCodeExample = () => {
    const currentAgent = AGENTS.find((a) => a.id === selectedAgent);
    const currentTool = currentAgent?.tools.find((t) => t.name === selectedTool);
    
    if (!currentAgent || !currentTool) {
      return '// Select a tool to see code example';
    }

    // Parse example input to get arguments
    let argumentsObj: any = {};
    try {
      argumentsObj = JSON.parse(currentTool.exampleInput);
    } catch (e) {
      argumentsObj = { example: currentTool.exampleInput };
    }

    // Build JSON-RPC request dynamically
    const request = {
      jsonrpc: '2.0',
      method: 'tools/invoke',
      params: {
        agentId: selectedAgent,
        toolName: selectedTool,
        arguments: argumentsObj,
      },
      id: 'req-1',
    };

    return JSON.stringify(request, null, 2);
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
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left Panel - Tool Selector & Invoker */}
      <div className="space-y-6">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Available Tools</h2>

          {/* Agent Selector */}
          <div className="space-y-2 mb-6">
            {AGENTS.map((agent) => (
              <div key={agent.id} className="space-y-2">
                <button
                  onClick={() => {
                    setSelectedAgent(agent.id);
                    setSelectedTool(agent.tools[0].name);
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
                          setInput('');
                          setResult(null);
                        }}
                        className={`w-full px-3 py-2 rounded text-left text-sm transition-colors ${
                          selectedTool === tool.name
                            ? 'bg-slate-600 text-white'
                            : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                        }`}
                      >
                        <div className="font-mono">{tool.name}</div>
                        <div className="text-xs opacity-75">{tool.description}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Invoke Panel */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-md font-semibold text-white">Test Tool</h3>
            {currentTool?.exampleInput && (
              <button
                onClick={() => setInput(currentTool.exampleInput)}
                className="text-xs px-3 py-1 bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
              >
                Use Example
              </button>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Input</label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={currentTool?.placeholder || 'Enter input...'}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-100 text-sm font-mono placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={6}
            />
          </div>

          <button
            onClick={invokeTool}
            disabled={loading || (!input && selectedTool !== 'tool_list_content')}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Invoking...' : 'Invoke Tool'}
          </button>

          {result && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Result</label>
              <pre className="bg-slate-900 p-3 rounded-lg text-xs overflow-x-auto text-green-400 border border-slate-600 max-h-96">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Code Examples */}
      <div className="space-y-6">
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Code Example</h2>
          <pre className="bg-slate-900 p-4 rounded-lg text-xs overflow-x-auto border border-slate-600">
            <code className="text-blue-300">{getCodeExample()}</code>
          </pre>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-md font-semibold text-white mb-3">Integration Guide</h3>
          <div className="space-y-3 text-sm text-slate-300">
            <div>
              <p className="font-medium text-slate-200">1. Connect to MCP Server</p>
              <pre className="mt-1 bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600">
{`const ws = new WebSocket('ws://localhost:4000');`}
              </pre>
            </div>

            <div>
              <p className="font-medium text-slate-200">2. Send JSON-RPC Request via WebSocket</p>
              <pre className="mt-1 bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600">
{`// Send the request from the code example above
const request = ${getCodeExample()};
ws.send(JSON.stringify(request));`}
              </pre>
            </div>

            <div>
              <p className="font-medium text-slate-200">3. Listen for Response</p>
              <pre className="mt-1 bg-slate-900 p-2 rounded text-xs text-blue-300 border border-slate-600">
{`ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.result);
};`}
              </pre>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-md font-semibold text-white mb-3">
            {selectedAgent === 'storage-agent' ? 'Storage Agent Schema' : 
             selectedAgent === 'metadata-extraction-agent' ? 'Metadata Extraction Tool' :
             selectedAgent === 'sample-agent' ? 'Sample Agent Tools' : 'Tool Details'}
          </h3>
          <div className="text-xs space-y-3 text-slate-300">
            {selectedAgent === 'storage-agent' && (
              <>
                <div>
                  <p className="font-medium text-slate-200">Document Fields:</p>
                  <div className="text-slate-400 space-y-1 ml-2 mt-1">
                    <div><code className="text-blue-300">type</code> - Document type (ocr, transcription, etc)</div>
                    <div><code className="text-blue-300">original_file</code> - Source file name/path</div>
                    <div><code className="text-blue-300">file_format</code> - Format (pdf, txt, json)</div>
                    <div><code className="text-blue-300">processed_data</code> - Extracted content (JSON)</div>
                    <div><code className="text-blue-300">metadata</code> - Document metadata (JSON)</div>
                    <div><code className="text-blue-300">app_data</code> - App-specific data (JSON)</div>
                    <div><code className="text-blue-300">created_by</code> - Creator identifier</div>
                  </div>
                </div>
                <div>
                  <p className="font-medium text-slate-200">Available Tools (8 total):</p>
                  <div className="text-slate-400 space-y-1 ml-2 mt-1">
                    <div>• store_document, retrieve_document, list_documents</div>
                    <div>• get_stats, delete_all_documents, answer_content_query</div>
                    <div>• list_backends, list_storage_providers</div>
                  </div>
                </div>
              </>
            )}
            {selectedAgent === 'metadata-extraction-agent' && (
              <div>
                <p className="font-medium text-slate-200">extract_metadata Parameters:</p>
                <div className="text-slate-400 space-y-1 ml-2 mt-1">
                  <div><code className="text-blue-300">text</code> - Input text to extract metadata from</div>
                  <div><code className="text-blue-300">model</code> - AI model to use (e.g., "claude")</div>
                  <div><code className="text-blue-300">output_type</code> - Output format (e.g., "pala")</div>
                </div>
              </div>
            )}
            {selectedAgent === 'sample-agent' && (
              <>
                <div>
                  <p className="font-medium text-slate-200">echo Parameters:</p>
                  <div className="text-slate-400 space-y-1 ml-2 mt-1">
                    <div><code className="text-blue-300">text</code> - Text to echo back</div>
                  </div>
                </div>
                <div>
                  <p className="font-medium text-slate-200">sum Parameters:</p>
                  <div className="text-slate-400 space-y-1 ml-2 mt-1">
                    <div><code className="text-blue-300">numbers</code> - Array of numbers to sum</div>
                  </div>
                </div>
              </>
            )}
          </div>
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
