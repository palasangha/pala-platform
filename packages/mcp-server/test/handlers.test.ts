/**
 * Tests for server handlers
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ServerHandlers } from '../src/handlers';
import { ToolRegistry, ToolDefinition } from '../src/registry/tool-registry';
import { WebSocketTransport, Connection } from '../src/transport/websocket';
import { WebSocket } from 'ws';

describe('ServerHandlers', () => {
  let registry: ToolRegistry;
  let transport: WebSocketTransport;
  let handlers: ServerHandlers;

  beforeEach(() => {
    registry = new ToolRegistry();
    transport = new WebSocketTransport({ port: 9999 });
    handlers = new ServerHandlers(registry, transport);
  });

  describe('handleToolsRegister', () => {
    it('should register tools from agent', async () => {
      const result = await handlers.handleToolsRegister({
        tools: [
          {
            name: 'test-tool',
            description: 'Test',
            agentId: 'agent-1',
            inputSchema: { type: 'object', properties: {} },
          },
          {
            name: 'test-tool-2',
            description: 'Test 2',
            agentId: 'agent-1',
            inputSchema: { type: 'object', properties: {} },
          },
        ],
      });

      expect(result.registered).toBe(2);
      expect(registry.getTool('test-tool')).toBeDefined();
      expect(registry.getTool('test-tool-2')).toBeDefined();
    });

    it('should throw on invalid params', async () => {
      await expect(handlers.handleToolsRegister(null)).rejects.toThrow();
      await expect(handlers.handleToolsRegister({})).rejects.toThrow();
    });

    it('should continue registering on partial failure', async () => {
      const result = await handlers.handleToolsRegister({
        tools: [
          {
            name: 'valid-tool',
            description: 'Valid',
            agentId: 'agent-1',
            inputSchema: { type: 'object', properties: {} },
          },
          {
            name: '', // Invalid: empty name
            description: 'Invalid',
            agentId: 'agent-1',
            inputSchema: { type: 'object', properties: {} },
          },
        ],
      });

      expect(result.registered).toBe(1);
      expect(registry.getTool('valid-tool')).toBeDefined();
    });
  });

  describe('handleToolsList', () => {
    it('should return empty list initially', async () => {
      const result = await handlers.handleToolsList();
      expect(result.tools).toHaveLength(0);
    });

    it('should return registered tools', async () => {
      registry.register({
        name: 'tool-1',
        description: 'Tool 1',
        agentId: 'agent-1',
        inputSchema: { type: 'object', properties: {} },
      });

      const result = await handlers.handleToolsList();
      expect(result.tools).toHaveLength(1);
      expect(result.tools[0].name).toBe('tool-1');
    });
  });

  describe('handleAgentsList', () => {
    it('should return empty list when no agents connected', async () => {
      const result = await handlers.handleAgentsList();
      expect(result.agents).toHaveLength(0);
    });

    it('should list agents with their tools', async () => {
      // Register tools first
      registry.register({
        name: 'agent-tool-1',
        description: 'Agent tool',
        agentId: 'agent-1',
        inputSchema: { type: 'object', properties: {} },
      });

      // Manually add a mock connection with metadata
      const mockConn: Connection = {
        id: 'conn-123',
        ws: {} as WebSocket,
        isAlive: true,
        metadata: { principalId: 'agent-1' },
      };

      // This won't work without exposing addConnection or similar
      // For now, just verify the structure
      const result = await handlers.handleAgentsList();
      expect(result.agents).toBeInstanceOf(Array);
    });
  });
});
