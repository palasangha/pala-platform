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
  // Always connect to MCP server on localhost:3000
  // (Next.js may run on a different port like 3001)
  const { connected, error: wsError, send } = useWebSocket('ws://localhost:3000');

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [invocationArgs, setInvocationArgs] = useState('{}');
  const [invocationResult, setInvocationResult] = useState<InvocationResult | null>(null);
  const [invoking, setInvoking] = useState(false);

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

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Agents & Tools */}
          <div className="lg:col-span-2 space-y-8">
            {/* Agents Section */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Connected Agents</h2>
              </div>
              <div className="p-6">
                {agents.length === 0 ? (
                  <p className="text-gray-600">No agents connected</p>
                ) : (
                  <div className="space-y-4">
                    {agents.map((agent) => (
                      <div key={agent.id} className="border border-gray-200 rounded-lg p-4">
                        <h3 className="font-semibold text-gray-900">{agent.id}</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          {agent.tools.length} tool{agent.tools.length !== 1 ? 's' : ''}
                        </p>
                        {agent.tools.length > 0 && (
                          <ul className="mt-3 space-y-2">
                            {agent.tools.map((tool) => (
                              <li key={tool.name} className="text-sm text-gray-700 ml-4">
                                • <span className="font-mono font-medium">{tool.name}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Tools Section */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Available Tools</h2>
              </div>
              <div className="p-6">
                {tools.length === 0 ? (
                  <p className="text-gray-600">No tools registered</p>
                ) : (
                  <div className="space-y-4">
                    {tools.map((tool) => (
                      <div
                        key={`${tool.agentId}-${tool.name}`}
                        className={`border rounded-lg p-4 cursor-pointer transition ${
                          selectedTool?.name === tool.name && selectedTool?.agentId === tool.agentId
                            ? 'border-blue-600 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => setSelectedTool(tool)}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                            <p className="text-sm text-gray-600 mt-1">{tool.description}</p>
                            <p className="text-xs text-gray-500 mt-2">Agent: {tool.agentId}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tool Invocation */}
          <div className="bg-white rounded-lg shadow h-fit sticky top-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Invoke Tool</h2>
            </div>
            <div className="p-6 space-y-4">
              {selectedTool ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Tool</label>
                    <p className="mt-2 px-3 py-2 bg-gray-50 rounded text-sm text-gray-900">
                      {selectedTool.name}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Arguments (JSON)</label>
                    <textarea
                      value={invocationArgs}
                      onChange={(e) => setInvocationArgs(e.target.value)}
                      className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
                      rows={4}
                    />
                  </div>
                  <button
                    onClick={handleInvokeTool}
                    disabled={invoking || !connected}
                    className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
                  >
                    {invoking ? 'Invoking...' : 'Invoke'}
                  </button>
                  {invocationResult && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                      {invocationResult.error ? (
                        <div className="text-sm text-red-700">
                          <p className="font-semibold">Error</p>
                          <p className="mt-1">{invocationResult.error}</p>
                        </div>
                      ) : (
                        <div className="text-sm text-gray-700">
                          <p className="font-semibold">Result</p>
                          <pre className="mt-2 whitespace-pre-wrap break-words text-xs bg-white p-2 rounded border border-gray-200">
                            {JSON.stringify(invocationResult.result, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-gray-600 text-sm">Select a tool to invoke</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
