/**
 * Tests for WebSocket Transport Layer
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketTransport } from '../../src/transport/websocket';
import { ProtocolHandler } from '../../src/protocol/handler';
import WebSocket from 'ws';
import jwt from 'jsonwebtoken';

describe('WebSocketTransport', () => {
  let transport: WebSocketTransport;
  let protocolHandler: ProtocolHandler;
  const TEST_PORT = 9876;

  beforeEach(async () => {
    transport = new WebSocketTransport({ port: TEST_PORT });
    protocolHandler = new ProtocolHandler();
    transport.setProtocolHandler(protocolHandler);
  });

  afterEach(async () => {
    // Only stop if transport has an active server
    if ((transport as any).httpServer) {
      await transport.stop();
    }
  });

  describe('lifecycle', () => {
    it('should start server successfully', async () => {
      const listeningPromise = new Promise((resolve) => {
        transport.on('listening', resolve);
      });

      await transport.start();
      await listeningPromise;

      expect(transport.getConnectionCount()).toBe(0);
    });

    it('should stop server cleanly', async () => {
      await transport.start();
      
      const closedPromise = new Promise((resolve) => {
        transport.on('closed', resolve);
      });

      await transport.stop();
      await closedPromise;
    });
  });

  describe('connections', () => {
    it('should accept client connections', async () => {
      await transport.start();

      const connectionPromise = new Promise((resolve) => {
        transport.on('connection', resolve);
      });

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      await connectionPromise;
      expect(transport.getConnectionCount()).toBe(1);

      client.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should handle multiple connections', async () => {
      await transport.start();

      const clients: WebSocket[] = [];
      for (let i = 0; i < 3; i++) {
        const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
        await new Promise((resolve) => client.on('open', resolve));
        clients.push(client);
      }

      await new Promise((resolve) => setTimeout(resolve, 100));
      expect(transport.getConnectionCount()).toBe(3);

      clients.forEach((c) => c.close());
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should track connection disconnects', async () => {
      await transport.start();

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      const disconnectPromise = new Promise((resolve) => {
        transport.on('disconnect', resolve);
      });

      client.close();
      await disconnectPromise;

      expect(transport.getConnectionCount()).toBe(0);
    });
  });

  describe('message handling', () => {
    it('should process valid JSON-RPC messages', async () => {
      await transport.start();

      // Register a test handler
      protocolHandler.registerHandler('test.echo', async (method, params: any) => {
        return { echoed: params };
      });

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      const responsePromise = new Promise<string>((resolve) => {
        client.on('message', (data) => {
          resolve(data.toString());
        });
      });

      const request = JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'test.echo',
        params: { message: 'hello' },
      });

      client.send(request);
      const response = await responsePromise;
      const parsed = JSON.parse(response);

      expect(parsed.jsonrpc).toBe('2.0');
      expect(parsed.id).toBe(1);
      expect(parsed.result.echoed.message).toBe('hello');

      client.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should return error for invalid JSON', async () => {
      await transport.start();

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      const responsePromise = new Promise<string>((resolve) => {
        client.on('message', (data) => {
          resolve(data.toString());
        });
      });

      client.send('{invalid json}');
      const response = await responsePromise;
      const parsed = JSON.parse(response);

      expect(parsed.error).toBeDefined();
      expect(parsed.error.code).toBe(-32700); // Parse error

      client.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should handle notifications without response', async () => {
      await transport.start();

      let notificationReceived = false;
      protocolHandler.registerHandler('notify.test', async () => {
        notificationReceived = true;
      });

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      // Set up message listener to ensure no response
      let receivedMessage = false;
      client.on('message', () => {
        receivedMessage = true;
      });

      const notification = JSON.stringify({
        jsonrpc: '2.0',
        method: 'notify.test',
        params: { data: 'test' },
      });

      client.send(notification);
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(notificationReceived).toBe(true);
      expect(receivedMessage).toBe(false); // No response for notifications

      client.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });
  });

  describe('send and broadcast', () => {
    it('should send message to specific connection', async () => {
      await transport.start();

      const connectionPromise = new Promise<any>((resolve) => {
        transport.on('connection', resolve);
      });

      const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
      await new Promise((resolve) => client.on('open', resolve));

      const connection = await connectionPromise;

      const messagePromise = new Promise<string>((resolve) => {
        client.on('message', (data) => resolve(data.toString()));
      });

      const success = transport.send(connection.id, 'test message');
      expect(success).toBe(true);

      const message = await messagePromise;
      expect(message).toBe('test message');

      client.close();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    it('should broadcast to all connections', async () => {
      await transport.start();

      const clients: WebSocket[] = [];
      const messages: string[] = [];

      for (let i = 0; i < 3; i++) {
        const client = new WebSocket(`ws://localhost:${TEST_PORT}`);
        await new Promise((resolve) => client.on('open', resolve));
        client.on('message', (data) => messages.push(data.toString()));
        clients.push(client);
      }

      await new Promise((resolve) => setTimeout(resolve, 100));

      transport.broadcast('broadcast message');
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(messages).toHaveLength(3);
      expect(messages.every((m) => m === 'broadcast message')).toBe(true);

      clients.forEach((c) => c.close());
      await new Promise((resolve) => setTimeout(resolve, 100));
    });
  });

  describe('heartbeat', () => {
    it('should send ping to connections', async () => {
      // Use different port to avoid conflicts with main transport
      const customPort = TEST_PORT + 100;
      const shortPingTransport = new WebSocketTransport({
        port: customPort,
        pingInterval: 100,
      });
      shortPingTransport.setProtocolHandler(protocolHandler);

      try {
        await shortPingTransport.start();

        const client = new WebSocket(`ws://localhost:${customPort}`);
        await new Promise((resolve) => client.on('open', resolve));

        let pingReceived = false;
        client.on('ping', () => {
          pingReceived = true;
        });

        await new Promise((resolve) => setTimeout(resolve, 200));
        expect(pingReceived).toBe(true);

        client.close();
        await new Promise((resolve) => setTimeout(resolve, 50));
      } finally {
        // Ensure cleanup happens even if test fails
        await shortPingTransport.stop();
      }
    });
  });

  describe('auth', () => {
    const AUTH_PORT = TEST_PORT + 200;
    const SECRET = 'test-secret';

    it('should accept connection with valid JWT', async () => {
      const authTransport = new WebSocketTransport({
        port: AUTH_PORT,
        auth: {
          enabled: true,
          sharedSecret: SECRET,
        },
      });

      await authTransport.start();

      try {
        const token = jwt.sign({ sub: 'agent-1' }, SECRET);
        const client = new WebSocket(`ws://localhost:${AUTH_PORT}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        await new Promise((resolve, reject) => {
          client.on('open', resolve);
          client.on('error', reject);
        });

        const connections = authTransport.getConnections();
        expect(connections).toHaveLength(1);
        expect(connections[0].metadata?.principalId).toBe('agent-1');

        client.close();
        await new Promise((resolve) => setTimeout(resolve, 50));
      } finally {
        await authTransport.stop();
      }
    });

    it('should reject connection without token when auth enabled', async () => {
      const authTransport = new WebSocketTransport({
        port: AUTH_PORT + 1,
        auth: {
          enabled: true,
          sharedSecret: SECRET,
        },
      });

      await authTransport.start();

      try {
        const client = new WebSocket(`ws://localhost:${AUTH_PORT + 1}`);

        await expect(
          new Promise((resolve, reject) => {
            client.on('open', () => reject(new Error('should not open')));
            client.on('error', () => resolve(true));
            client.on('close', () => resolve(true));
          })
        ).resolves.toBe(true);

        expect(authTransport.getConnectionCount()).toBe(0);
      } finally {
        await authTransport.stop();
      }
    });
  });
});
