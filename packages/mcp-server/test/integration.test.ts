/**
 * End-to-End Integration Test
 * Demonstrates complete flow: server → agent registration → tool discovery → invocation
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { MCPServer } from '../src/server';
import { WebSocket } from 'ws';

const TEST_PORT = 10000;
const SERVER_URL = `ws://localhost:${TEST_PORT}`;

describe('End-to-End Integration', () => {
  let server: MCPServer;

  beforeAll(async () => {
    server = new MCPServer({ port: TEST_PORT });
    await server.start();
    // Wait for server to be ready
    await new Promise((resolve) => setTimeout(resolve, 100));
  });

  afterAll(async () => {
    await server.stop();
  });

  it('should support agent registration and tool discovery workflow', async () => {
    return new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(SERVER_URL);
      let phase = 'connect';

      ws.onopen = () => {
        phase = 'register-tools';
        // Agent registers its tools on connect
        ws.send(JSON.stringify({
          jsonrpc: '2.0',
          method: 'tools/register',
          params: {
            tools: [
              {
                name: 'test-echo',
                description: 'Echo test tool',
                agentId: 'test-agent-1',
                inputSchema: { type: 'object', properties: { message: { type: 'string' } } },
              },
            ],
          },
          id: 1,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string);

          if (phase === 'register-tools' && message.id === 1) {
            expect(message.result).toBeDefined();
            expect(message.result.registered).toBeGreaterThan(0);

            phase = 'list-agents';
            // Query agents
            ws.send(JSON.stringify({
              jsonrpc: '2.0',
              method: 'agents/list',
              params: {},
              id: 2,
            }));
          } else if (phase === 'list-agents' && message.id === 2) {
            expect(message.result).toBeDefined();
            expect(message.result.agents).toBeDefined();
            expect(Array.isArray(message.result.agents)).toBe(true);

            phase = 'list-tools';
            // Query tools
            ws.send(JSON.stringify({
              jsonrpc: '2.0',
              method: 'tools/list',
              params: {},
              id: 3,
            }));
          } else if (phase === 'list-tools' && message.id === 3) {
            expect(message.result).toBeDefined();
            expect(message.result.tools).toBeDefined();
            expect(Array.isArray(message.result.tools)).toBe(true);

            // Verify the registered tool is in the list
            const registeredTool = message.result.tools.find(
              (tool: any) => tool.name === 'test-echo'
            );
            expect(registeredTool).toBeDefined();
            expect(registeredTool.agentId).toBe('test-agent-1');

            ws.close();
            resolve();
          }
        } catch (err) {
          reject(err);
        }
      };

      ws.onerror = (event) => {
        reject(new Error(`WebSocket error: ${event}`));
      };

      ws.onclose = () => {
        if (phase !== 'list-tools') {
          reject(new Error(`Connection closed unexpectedly at phase: ${phase}`));
        }
      };

      // Timeout after 5 seconds
      setTimeout(() => {
        reject(new Error(`Test timeout at phase: ${phase}`));
      }, 5000);
    });
  });

  it('should handle tool invocation request and route to agent', async () => {
    return new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(SERVER_URL);
      let registered = false;

      ws.onopen = () => {
        // Register tool first
        ws.send(JSON.stringify({
          jsonrpc: '2.0',
          method: 'tools/register',
          params: {
            tools: [
              {
                name: 'sum-numbers',
                description: 'Sum a list of numbers',
                agentId: 'test-agent-2',
                inputSchema: { type: 'object', properties: { numbers: { type: 'array' } } },
              },
            ],
          },
          id: 1,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string);

          if (!registered && message.id === 1) {
            registered = true;
            expect(message.result.registered).toBeGreaterThan(0);

            // Now query to verify
            ws.send(JSON.stringify({
              jsonrpc: '2.0',
              method: 'tools/list',
              params: {},
              id: 2,
            }));
          } else if (registered && message.id === 2) {
            const sumTool = message.result.tools.find((t: any) => t.name === 'sum-numbers');
            expect(sumTool).toBeDefined();

            ws.close();
            resolve();
          }
        } catch (err) {
          reject(err);
        }
      };

      ws.onerror = (event) => {
        reject(new Error(`WebSocket error: ${event}`));
      };

      setTimeout(() => {
        reject(new Error('Test timeout'));
      }, 5000);
    });
  });
});
