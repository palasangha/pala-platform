'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

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

interface InvocationResult {
  result?: unknown;
  error?: string;
}

export default function Dashboard() {
  // Connect to MCP server - handle both client-side and SSR
  const [wsUrl, setWsUrl] = useState('');
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Determine the correct WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      // Try port 3000 first (where MCP server runs), fallback to same port
      setWsUrl(`${protocol}//${host}:3000`);
    }
  }, []);

  const { connected, error: wsError, send } = useWebSocket(wsUrl);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [invocationArgs, setInvocationArgs] = useState('{}');
  const [invocationResult, setInvocationResult] = useState<InvocationResult | null>(null);
  const [invoking, setInvoking] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('sample-agent');

  const getToolPlaceholder = (toolName: string): string => {
    switch (toolName) {
      case 'echo':
        return '{"text": "hello world"}';
      case 'sum':
        return '{"numbers": [1, 2, 3, 4, 5]}';
      case 'extract_metadata':
        return JSON.stringify({
          ocr_text: "Letter dated 15th March 1892\n\nDear Venerable Sir,\n\nI write to inform you of the monastery's administrative matters. The construction of the new meditation hall has progressed well under the supervision of Brother Thomas. We anticipate completion by June.\n\nRespectfully yours,\nJohn Smith\nSecretary, Monastery Board",
          model: "claude",
          output_type: "combined",
          language: "en",
          document_context: "historical_letter"
        }, null, 2);
      default:
        return '{}';
    }
  };

  const getToolHint = (toolName: string): string => {
    switch (toolName) {
      case 'echo':
        return 'Example: {"text": "hello world"}';
      case 'sum':
        return 'Example: {"numbers": [1, 2, 3, 4, 5]}';
      case 'extract_metadata':
        return 'Required: ocr_text (string), model ("claude"), output_type ("pala" | "archipelago" | "combined"). Optional: language (ISO code), document_context (e.g., "historical_letter"), custom_prompt (string), schema_version ("1.0.0")';
      default:
        return 'Enter JSON arguments for this tool';
    }
  };

  useEffect(() => {
    if (connected) {
      refreshData();
    }
  }, [connected]);

  const refreshData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [agentsData, toolsData] = await Promise.all([
        send('agents/list', {}),
        send('tools/list', {}),
      ]);

      setAgents((agentsData as any).agents || []);
      setTools((toolsData as any).tools || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleInvokeTool = async () => {
    if (!selectedTool) return;

    try {
      setInvoking(true);
      const args = JSON.parse(invocationArgs);
      const result = await send('tools/invoke', {
        toolName: selectedTool.name,
        agentId: selectedTool.agentId,
        arguments: args,
      });
      setInvocationResult({ result });
    } catch (err) {
      setInvocationResult({
        error: err instanceof Error ? err.message : 'Invocation failed',
      });
    } finally {
      setInvoking(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">MCP Server Dashboard</h1>
          <p className="mt-2 text-gray-600">Manage agents and invoke tools</p>
          <div className="mt-4 flex items-center gap-2">
            <div className={`status-indicator ${connected ? 'connected' : wsError ? 'disconnected' : 'connecting'}`} />
            <span className="text-sm font-medium">
              {connected ? 'Connected' : wsError ? 'Disconnected' : 'Connecting...'}
            </span>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Refresh Button */}
        <div className="mb-6">
          <button
            onClick={refreshData}
            disabled={!connected || loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh Data'}
          </button>
        </div>

        {/* Agent Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {['sample-agent', 'metadata-extraction-agent'].map((agentId) => {
              const agent = agents.find(a => a.id === agentId);
              const isActive = activeTab === agentId;
              return (
                <button
                  key={agentId}
                  onClick={() => {
                    setActiveTab(agentId);
                    setSelectedTool(null);
                    setInvocationResult(null);
                  }}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${isActive
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                    ${!agent ? 'opacity-50' : ''}
                  `}
                  disabled={!agent}
                >
                  {agentId === 'sample-agent' ? 'Sample Agent' : 'Metadata Extraction'}
                  {agent && (
                    <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                      {agent.tools.length}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Top Row - Agent Info & Available Tools side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Current Agent Info */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">
                  {activeTab === 'sample-agent' ? 'Sample Agent' : 'Metadata Extraction Agent'}
                </h2>
              </div>
              <div className="p-6">
                {(() => {
                  const currentAgent = agents.find(a => a.id === activeTab);
                  if (!currentAgent) {
                    return (
                      <p className="text-gray-600">
                        Agent not connected. Please start the agent and refresh.
                      </p>
                    );
                  }
                  return (
                    <div className="border border-gray-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900">{currentAgent.id}</h3>
                      <p className="text-sm text-gray-600 mt-1">
                        {currentAgent.tools.length} tool{currentAgent.tools.length !== 1 ? 's' : ''} available
                      </p>
                      {currentAgent.tools.length > 0 && (
                        <ul className="mt-3 space-y-2">
                          {currentAgent.tools.map((tool) => (
                            <li key={tool.name} className="text-sm text-gray-700 ml-4">
                              • <span className="font-mono font-medium">{tool.name}</span> - {tool.description}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Tools Section */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Available Tools</h2>
              </div>
              <div className="p-6">
                {(() => {
                  const agentTools = tools.filter(t => t.agentId === activeTab);
                  if (agentTools.length === 0) {
                    return <p className="text-gray-600">No tools available for this agent</p>;
                  }
                  return (
                    <div className="space-y-3">
                      {agentTools.map((tool) => (
                        <div
                          key={`${tool.agentId}-${tool.name}`}
                          className={`border rounded-lg p-3 cursor-pointer transition ${
                            selectedTool?.name === tool.name && selectedTool?.agentId === tool.agentId
                            ? 'border-blue-600 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => setSelectedTool(tool)}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                            <p className="text-xs text-gray-600 mt-1">{tool.description}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>

          {/* Invoke Tool Section */}
          {selectedTool ? (
            <>
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">Invoke: {selectedTool.name}</h2>
                  <p className="text-sm text-gray-600 mt-1">{selectedTool.description}</p>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left - Sample JSON */}
                    <div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <p className="text-xs font-semibold text-blue-900 uppercase">Sample Input</p>
                          <button
                            onClick={() => setInvocationArgs(getToolPlaceholder(selectedTool.name))}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                          >
                            Use Sample →
                          </button>
                        </div>
                        <pre className="text-xs text-blue-900 overflow-x-auto whitespace-pre-wrap break-words max-h-[400px] overflow-y-auto">
                          {getToolPlaceholder(selectedTool.name)}
                        </pre>
                      </div>
                      <p className="mt-2 text-xs text-gray-500">
                        {getToolHint(selectedTool.name)}
                      </p>
                    </div>

                    {/* Right - Arguments Input */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Arguments (JSON)
                      </label>
                      <textarea
                        value={invocationArgs}
                        onChange={(e) => setInvocationArgs(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                        rows={16}
                        placeholder={getToolPlaceholder(selectedTool.name)}
                      />
                      <button
                        onClick={handleInvokeTool}
                        disabled={invoking || !connected}
                        className="w-full mt-4 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-semibold text-base transition-colors"
                      >
                        {invoking ? 'Invoking...' : 'Invoke Tool'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Output Section */}
              {invocationResult && (
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">
                      {invocationResult.error ? '❌ Error' : '✅ Result'}
                    </h2>
                  </div>
                  <div className="p-6">
                    {invocationResult.error ? (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-sm text-red-800 whitespace-pre-wrap">
                          {invocationResult.error}
                        </p>
                      </div>
                    ) : (
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <pre className="text-xs text-gray-900 overflow-x-auto whitespace-pre-wrap break-words max-h-[600px] overflow-y-auto">
                          {JSON.stringify(invocationResult.result, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Invoke Tool</h2>
              </div>
              <div className="p-6">
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <p className="mt-4 text-gray-600">Select a tool from the list above to invoke</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
