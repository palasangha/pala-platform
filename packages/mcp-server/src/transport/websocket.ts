/**
 * WebSocket Transport Layer
 * Manages bidirectional communication with clients and agents
 */

import { WebSocketServer, WebSocket } from 'ws';
import { createServer, Server as HTTPServer } from 'http';
import { EventEmitter } from 'events';
import type { ProtocolHandler } from '../protocol/handler';

export interface TransportConfig {
  port: number;
  host?: string;
  pingInterval?: number; // ms, default 30000
  pingTimeout?: number; // ms, default 5000
}

export interface Connection {
  id: string;
  ws: WebSocket;
  type?: 'client' | 'agent';
  isAlive: boolean;
  metadata?: Record<string, unknown>;
}

export class WebSocketTransport extends EventEmitter {
  private wss?: WebSocketServer;
  private httpServer?: HTTPServer;
  private connections: Map<string, Connection>;
  private config: Required<TransportConfig>;
  private protocolHandler?: ProtocolHandler;
  private pingIntervalId?: NodeJS.Timeout;

  constructor(config: TransportConfig) {
    super();
    this.connections = new Map();
    this.config = {
      host: '0.0.0.0',
      pingInterval: 30000,
      pingTimeout: 5000,
      ...config,
    };
  }

  /**
   * Set protocol handler for message processing
   */
  setProtocolHandler(handler: ProtocolHandler): void {
    this.protocolHandler = handler;
  }

  /**
   * Start WebSocket server
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Create HTTP server
      this.httpServer = createServer();

      // Create WebSocket server
      this.wss = new WebSocketServer({ server: this.httpServer });

      // Handle new connections
      this.wss.on('connection', (ws: WebSocket) => {
        this.handleConnection(ws);
      });

      // Handle server errors
      this.wss.on('error', (error) => {
        this.emit('error', error);
      });

      // Start HTTP server
      this.httpServer.listen(this.config.port, this.config.host, () => {
        this.emit('listening', { port: this.config.port, host: this.config.host });
        this.startHeartbeat();
        resolve();
      });

      this.httpServer.on('error', reject);
    });
  }

  /**
   * Stop WebSocket server
   */
  async stop(): Promise<void> {
    return new Promise((resolve) => {
      this.stopHeartbeat();

      // Close all connections
      for (const connection of this.connections.values()) {
        connection.ws.close(1000, 'Server shutting down');
      }
      this.connections.clear();

      // Close WebSocket server
      this.wss?.close(() => {
        // Close HTTP server
        this.httpServer?.close(() => {
          this.emit('closed');
          resolve();
        });
      });
    });
  }

  /**
   * Handle new WebSocket connection
   */
  private handleConnection(ws: WebSocket): void {
    const connectionId = this.generateConnectionId();
    const connection: Connection = {
      id: connectionId,
      ws,
      isAlive: true,
    };

    this.connections.set(connectionId, connection);
    this.emit('connection', connection);

    // Handle incoming messages
    ws.on('message', async (data: Buffer) => {
      await this.handleMessage(connectionId, data.toString());
    });

    // Handle pong responses
    ws.on('pong', () => {
      const conn = this.connections.get(connectionId);
      if (conn) {
        conn.isAlive = true;
      }
    });

    // Handle connection close
    ws.on('close', (code: number, reason: Buffer) => {
      this.connections.delete(connectionId);
      this.emit('disconnect', { connectionId, code, reason: reason.toString() });
    });

    // Handle errors
    ws.on('error', (error) => {
      this.emit('connectionError', { connectionId, error });
    });
  }

  /**
   * Handle incoming message
   */
  private async handleMessage(connectionId: string, message: string): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) return;

    this.emit('message', { connectionId, message });

    if (!this.protocolHandler) {
      const errorResponse = JSON.stringify({
        jsonrpc: '2.0',
        id: null,
        error: {
          code: -32603,
          message: 'Internal error: Protocol handler not configured',
        },
      });
      connection.ws.send(errorResponse);
      return;
    }

    try {
      const response = await this.protocolHandler.processMessage(message);
      if (response) {
        connection.ws.send(response);
      }
    } catch (error) {
      const errorResponse = JSON.stringify({
        jsonrpc: '2.0',
        id: null,
        error: {
          code: -32603,
          message: 'Internal error',
          data: error instanceof Error ? error.message : 'Unknown error',
        },
      });
      connection.ws.send(errorResponse);
    }
  }

  /**
   * Send message to specific connection
   */
  send(connectionId: string, message: string): boolean {
    const connection = this.connections.get(connectionId);
    if (!connection || connection.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    connection.ws.send(message);
    return true;
  }

  /**
   * Broadcast message to all connections
   */
  broadcast(message: string, filter?: (conn: Connection) => boolean): void {
    for (const connection of this.connections.values()) {
      if (connection.ws.readyState === WebSocket.OPEN) {
        if (!filter || filter(connection)) {
          connection.ws.send(message);
        }
      }
    }
  }

  /**
   * Get connection by ID
   */
  getConnection(connectionId: string): Connection | undefined {
    return this.connections.get(connectionId);
  }

  /**
   * Get all active connections
   */
  getConnections(): Connection[] {
    return Array.from(this.connections.values());
  }

  /**
   * Get connection count
   */
  getConnectionCount(): number {
    return this.connections.size;
  }

  /**
   * Start heartbeat (ping/pong)
   */
  private startHeartbeat(): void {
    this.pingIntervalId = setInterval(() => {
      for (const [connectionId, connection] of this.connections.entries()) {
        if (!connection.isAlive) {
          // Connection didn't respond to last ping, terminate
          connection.ws.terminate();
          this.connections.delete(connectionId);
          this.emit('timeout', { connectionId });
          continue;
        }

        // Mark as not alive and send ping
        connection.isAlive = false;
        if (connection.ws.readyState === WebSocket.OPEN) {
          connection.ws.ping();
        }
      }
    }, this.config.pingInterval);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = undefined;
    }
  }

  /**
   * Generate unique connection ID
   */
  private generateConnectionId(): string {
    return `conn_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  }
}
