/**
 * Tests for Protocol Handler
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ProtocolHandler } from '../../src/protocol/handler';

describe('ProtocolHandler', () => {
  let handler: ProtocolHandler;

  beforeEach(() => {
    handler = new ProtocolHandler();
  });

  describe('registerHandler', () => {
    it('should register method handler', () => {
      const mockHandler = vi.fn().mockResolvedValue({ success: true });
      handler.registerHandler('test.method', mockHandler);

      expect(handler.getRegisteredMethods()).toContain('test.method');
    });

    it('should allow multiple handlers', () => {
      handler.registerHandler('method1', vi.fn());
      handler.registerHandler('method2', vi.fn());

      expect(handler.getRegisteredMethods()).toHaveLength(2);
    });
  });

  describe('unregisterHandler', () => {
    it('should remove method handler', () => {
      handler.registerHandler('test.method', vi.fn());
      handler.unregisterHandler('test.method');

      expect(handler.getRegisteredMethods()).not.toContain('test.method');
    });
  });

  describe('processMessage', () => {
    it('should process valid request', async () => {
      const mockHandler = vi.fn().mockResolvedValue({ data: 'response' });
      handler.registerHandler('test.method', mockHandler);

      const message = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'test.method',
        params: { input: 'test' },
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.jsonrpc).toBe('2.0');
      expect(parsed.id).toBe(1);
      expect(parsed.result).toEqual({ data: 'response' });
      expect(mockHandler).toHaveBeenCalledWith('test.method', { input: 'test' });
    });

    it('should return error for invalid JSON', async () => {
      const message = '{invalid json}';
      const response = await handler.processMessage(message);

      expect(response).toBeTruthy();
      const parsed = JSON.parse(response!);
      expect(parsed.error).toBeDefined();
      expect(parsed.error.code).toBe(-32700); // Parse error
    });

    it('should return error for invalid request structure', async () => {
      const message = JSON.stringify({
        jsonrpc: '2.0',
        // missing id and method
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.error).toBeDefined();
      expect(parsed.error.code).toBe(-32600); // Invalid request
    });

    it('should return error for unknown method', async () => {
      const message = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'unknown.method',
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.error).toBeDefined();
      expect(parsed.error.code).toBe(-32601); // Method not found
      expect(parsed.error.message).toContain('unknown.method');
    });

    it('should handle handler errors', async () => {
      const mockHandler = vi.fn().mockRejectedValue(new Error('Handler failed'));
      handler.registerHandler('failing.method', mockHandler);

      const message = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'failing.method',
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.error).toBeDefined();
      expect(parsed.error.code).toBe(-32603); // Internal error
      expect(parsed.error.data).toContain('Handler failed');
    });

    it('should handle notifications without response', async () => {
      const mockHandler = vi.fn().mockResolvedValue(undefined);
      handler.registerHandler('notify.event', mockHandler);

      const message = JSON.stringify({
        jsonrpc: '2.0',
        method: 'notify.event',
        params: { event: 'test' },
      });

      const response = await handler.processMessage(message);
      expect(response).toBeNull(); // No response for notifications
      expect(mockHandler).toHaveBeenCalledWith('notify.event', { event: 'test' });
    });

    it('should silently ignore notification errors', async () => {
      const mockHandler = vi.fn().mockRejectedValue(new Error('Notification failed'));
      handler.registerHandler('notify.event', mockHandler);

      const message = JSON.stringify({
        jsonrpc: '2.0',
        method: 'notify.event',
      });

      const response = await handler.processMessage(message);
      expect(response).toBeNull(); // Still no response
    });
  });

  describe('MCP Protocol Methods', () => {
    it('should handle initialize request', async () => {
      handler.registerHandler('initialize', async (method, params: any) => {
        return {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {},
          },
          serverInfo: {
            name: 'pala-mcp-server',
            version: '0.1.0',
          },
        };
      });

      const message = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'test-client', version: '1.0.0' },
        },
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.result.protocolVersion).toBe('2024-11-05');
      expect(parsed.result.serverInfo.name).toBe('pala-mcp-server');
    });

    it('should handle tools/list request', async () => {
      handler.registerHandler('tools/list', async () => {
        return {
          tools: [
            {
              name: 'extract_metadata',
              description: 'Extract metadata from content',
              inputSchema: {
                type: 'object',
                properties: {
                  contentId: { type: 'string' },
                },
                required: ['contentId'],
              },
            },
          ],
        };
      });

      const message = JSON.stringify({
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/list',
      });

      const response = await handler.processMessage(message);
      expect(response).toBeTruthy();

      const parsed = JSON.parse(response!);
      expect(parsed.result.tools).toHaveLength(1);
      expect(parsed.result.tools[0].name).toBe('extract_metadata');
    });
  });
});
