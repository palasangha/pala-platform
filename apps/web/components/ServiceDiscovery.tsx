'use client';

import { useEffect, useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

interface Agent {
  id: string;
  name: string;
  description?: string;
  status: 'ready' | 'loading' | 'error';
  tools: ToolDefinition[];
}

interface ToolDefinition {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  agentId: string;
}

interface ServiceDiscoveryProps {
  onAgentSelected?: (agentId: string) => void;
}

// Known agents and their tools
const KNOWN_AGENTS: Agent[] = [
  {
    id: 'sample-agent',
    name: 'Sample Agent',
    description: 'Example agent with echo and sum tools',
    status: 'ready',
    tools: [
      { name: 'echo', description: 'Echo back input text', agentId: 'sample-agent' },
      { name: 'sum', description: 'Sum array of numbers', agentId: 'sample-agent' },
    ],
  },
  {
    id: 'metadata-extraction-agent',
    name: 'Metadata Extraction Agent',
    description: 'Extract structured metadata from OCR text using Claude',
    status: 'ready',
    tools: [
      {
        name: 'extract_metadata',
        description: 'Extract metadata from OCR text',
        agentId: 'metadata-extraction-agent',
      },
      {
        name: 'extract_entities',
        description: 'Extract entities (people, places, organizations)',
        agentId: 'metadata-extraction-agent',
      },
    ],
  },
  {
    id: 'storage-agent',
    name: 'Storage Agent',
    description: 'Unified storage layer for all content',
    status: 'ready',
    tools: [
      {
        name: 'tool_store_document',
        description: 'Store document with automatic deduplication',
        agentId: 'storage-agent',
      },
      {
        name: 'tool_retrieve_content',
        description: 'Retrieve content by ID or hash',
        agentId: 'storage-agent',
      },
      {
        name: 'tool_search_content',
        description: 'Search stored content by metadata',
        agentId: 'storage-agent',
      },
    ],
  },
];

export function ServiceDiscovery({ onAgentSelected }: ServiceDiscoveryProps) {
  const { connected } = useWebSocket();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  useEffect(() => {
    // Set known agents immediately
    setAgents(KNOWN_AGENTS);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">
          Available Services
        </h2>
        <div
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            connected ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'
          }`}
        >
          {connected ? '● Connected' : '● Disconnected'}
        </div>
      </div>

      <div className="space-y-2">
        {agents.length === 0 ? (
          <div className="p-4 text-center text-slate-400">
            No services available
          </div>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.id}
              className="border border-slate-600 rounded-lg overflow-hidden bg-slate-700"
            >
              <button
                onClick={() =>
                  setExpandedAgent(expandedAgent === agent.id ? null : agent.id)
                }
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-600"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      agent.status === 'ready' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                  ></div>
                  <div className="text-left">
                    <p className="font-medium text-slate-100">{agent.name}</p>
                    {agent.description && (
                      <p className="text-xs text-slate-400">{agent.description}</p>
                    )}
                  </div>
                </div>
                <span className="text-xs font-medium text-slate-400">
                  {agent.tools.length} tools
                </span>
              </button>

              {expandedAgent === agent.id && (
                <div className="bg-slate-800 border-t border-slate-600 p-4 space-y-2">
                  {agent.tools.map((tool) => (
                    <div
                      key={`${agent.id}-${tool.name}`}
                      className="p-3 bg-slate-700 border border-slate-600 rounded text-sm"
                    >
                      <p className="font-mono font-medium text-slate-100">
                        {tool.name}
                      </p>
                      {tool.description && (
                        <p className="text-xs text-slate-400 mt-1">
                          {tool.description}
                        </p>
                      )}
                      <button
                        onClick={() => onAgentSelected?.(agent.id)}
                        className="mt-2 px-2 py-1 text-xs bg-blue-900 text-blue-200 rounded hover:bg-blue-800"
                      >
                        Test Tool
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
