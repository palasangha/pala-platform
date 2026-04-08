/**
 * Tests for Tool Invoker
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ToolInvoker, AgentConnection } from '../../src/registry/tool-invoker';
import { ToolRegistry, ToolDefinition } from '../../src/registry/tool-registry';

describe('ToolInvoker', () => {
  let registry: ToolRegistry;
  let invoker: ToolInvoker;
  let mockConnection: AgentConnection;
  let getAgentConnection: (agentId: string) => AgentConnection | undefined;

  const sampleTool: ToolDefinition = {
    name: 'test-tool',
    description: 'A test tool',
    agentId: 'agent-1',
    inputSchema: {
      type: 'object',
      properties: {
        input: { type: 'string' },
      },
      required: ['input'],
    },
  };

  beforeEach(() => {
    registry = new ToolRegistry();
    registry.register(sampleTool);

    mockConnection = {
      sendMessage: vi.fn().mockResolvedValue(undefined),
    };

    getAgentConnection = vi.fn((agentId: string) => {
      if (agentId === 'agent-1') return mockConnection;
      return undefined;
    });

    invoker = new ToolInvoker(registry, getAgentConnection);
  });

  describe('invoke', () => {
    it('should invoke a tool successfully', async () => {
      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test' },
      };

      // Simulate agent response after a delay
      setTimeout(() => {
        const calls = (mockConnection.sendMessage as any).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        invoker.handleInvocationResponse(lastCall.id, {
          data: { output: 'success' },
        });
      }, 50);

      const result = await invoker.invoke(request);

      expect(result.success).toBe(true);
      expect(result.result).toEqual({ output: 'success' });
      expect(result.agentId).toBe('agent-1');
      expect(result.toolName).toBe('test-tool');
    });

    it('should fail for non-existent tool', async () => {
      const result = await invoker.invoke({
        toolName: 'non-existent',
        arguments: {},
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Tool 'non-existent' not found");
    });

    it('should fail for invalid arguments', async () => {
      const result = await invoker.invoke({
        toolName: 'test-tool',
        arguments: {}, // missing required 'input'
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Missing required argument 'input'");
    });

    it('should fail when agent is not connected', async () => {
      registry.register({
        name: 'offline-tool',
        description: 'Tool for offline agent',
        agentId: 'agent-2',
        inputSchema: { type: 'object', properties: {} },
      });

      const result = await invoker.invoke({
        toolName: 'offline-tool',
        arguments: {},
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Agent 'agent-2' not connected");
    });

    it('should handle agent errors', async () => {
      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test' },
      };

      // Simulate agent error response
      setTimeout(() => {
        const calls = (mockConnection.sendMessage as any).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        invoker.handleInvocationResponse(lastCall.id, {
          error: 'Agent processing failed',
        });
      }, 50);

      const result = await invoker.invoke(request);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Agent processing failed');
    });

    it('should timeout if agent does not respond', async () => {
      invoker.setInvocationTimeout(100);

      const result = await invoker.invoke({
        toolName: 'test-tool',
        arguments: { input: 'test' },
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('timed out');
    }, 200);

    it('should emit invocation events', async () => {
      const startedSpy = vi.fn();
      const completedSpy = vi.fn();

      invoker.on('invocation:started', startedSpy);
      invoker.on('invocation:completed', completedSpy);

      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test' },
      };

      // Simulate agent response
      setTimeout(() => {
        const calls = (mockConnection.sendMessage as any).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        invoker.handleInvocationResponse(lastCall.id, {
          data: { output: 'success' },
        });
      }, 50);

      await invoker.invoke(request);

      const startedArg = startedSpy.mock.calls[0][0];
      expect(startedArg.traceId).toBeDefined();
      expect(startedArg.toolName).toBe('test-tool');
      expect(startedArg.arguments).toEqual({ input: 'test' });
      expect(completedSpy).toHaveBeenCalled();
    });

    it('should propagate provided traceId', async () => {
      const traceId = 'trace-123';
      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test' },
        traceId,
      };

      setTimeout(() => {
        const calls = (mockConnection.sendMessage as any).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        invoker.handleInvocationResponse(lastCall.id, {
          data: { output: 'success' },
        });
      }, 20);

      const result = await invoker.invoke(request);
      expect(result.traceId).toBe(traceId);
    });

    it('should emit failed event on error', async () => {
      const failedSpy = vi.fn();
      invoker.on('invocation:failed', failedSpy);

      const result = await invoker.invoke({
        toolName: 'non-existent',
        arguments: {},
      });

      expect(failedSpy).toHaveBeenCalled();
      expect(result.success).toBe(false);
    });

    it('should use provided requestId', async () => {
      const customId = 'custom-request-123';
      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test' },
        requestId: customId,
      };

      // Simulate agent response
      setTimeout(() => {
        invoker.handleInvocationResponse(customId, {
          data: { output: 'success' },
        });
      }, 50);

      const result = await invoker.invoke(request);

      expect(result.success).toBe(true);
      expect(mockConnection.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({ id: customId })
      );
    });
  });

  describe('timeout management', () => {
    it('should set invocation timeout', () => {
      invoker.setInvocationTimeout(5000);
      expect(invoker.getInvocationTimeout()).toBe(5000);
    });

    it('should reject invalid timeout values', () => {
      expect(() => invoker.setInvocationTimeout(0)).toThrow();
      expect(() => invoker.setInvocationTimeout(-100)).toThrow();
    });
  });

  describe('pending invocations', () => {
    it('should track pending invocations', async () => {
      expect(invoker.getPendingCount()).toBe(0);

      const promise = invoker.invoke({
        toolName: 'test-tool',
        arguments: { input: 'test' },
      });

      // Check after invocation started but before response
      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(invoker.getPendingCount()).toBe(1);

      // Complete the invocation
      const calls = (mockConnection.sendMessage as any).mock.calls;
      const lastCall = calls[calls.length - 1][0];
      invoker.handleInvocationResponse(lastCall.id, {
        data: { output: 'success' },
      });

      await promise;
      expect(invoker.getPendingCount()).toBe(0);
    });

    it('should clear pending invocations', async () => {
      invoker.setInvocationTimeout(1000);

      const promise = invoker.invoke({
        toolName: 'test-tool',
        arguments: { input: 'test' },
      });

      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(invoker.getPendingCount()).toBe(1);

      invoker.clearPending();
      expect(invoker.getPendingCount()).toBe(0);

      const result = await promise;
      expect(result.success).toBe(false);
      expect(result.error).toContain('cancelled');
    });

    it('should ignore responses for unknown invocations', () => {
      // Should not throw
      expect(() => {
        invoker.handleInvocationResponse('unknown-id', { data: 'test' });
      }).not.toThrow();
    });
  });

  describe('agent communication', () => {
    it('should send correct message format to agent', async () => {
      const request = {
        toolName: 'test-tool',
        arguments: { input: 'test-value' },
      };

      setTimeout(() => {
        const calls = (mockConnection.sendMessage as any).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        invoker.handleInvocationResponse(lastCall.id, {
          data: { output: 'success' },
        });
      }, 50);

      await invoker.invoke(request);

      expect(mockConnection.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          jsonrpc: '2.0',
          method: 'tools/invoke',
          params: {
            name: 'test-tool',
            arguments: { input: 'test-value' },
          },
          id: expect.any(String),
          traceId: expect.any(String),
        })
      );
    });

    it('should handle connection send errors', async () => {
      mockConnection.sendMessage = vi.fn().mockRejectedValue(new Error('Network error'));

      const result = await invoker.invoke({
        toolName: 'test-tool',
        arguments: { input: 'test' },
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });
  });
});
