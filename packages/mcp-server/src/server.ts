/**
 * Main MCP Server class
 * Orchestrates protocol, transport, registry, auth, and logging
 */

import type { ServerConfig } from './types';
import { WebSocketTransport } from './transport/websocket';
import { ProtocolHandler } from './protocol/handler';
import { ToolRegistry } from './registry/tool-registry';
import { ToolInvoker } from './registry/tool-invoker';
import { ServerHandlers } from './handlers';
import { Logger } from './logging/logger';
import { WebSocket } from 'ws';

const logger = new Logger({ name: 'MCPServer', level: (process.env.LOG_LEVEL as any) || 'info' });

export class MCPServer {
  private config: ServerConfig;
  private transport?: WebSocketTransport;
  private protocolHandler?: ProtocolHandler;
  private registry?: ToolRegistry;
  private invoker?: ToolInvoker;
  private handlers?: ServerHandlers;
  private agentConnections: Map<string, string> = new Map(); // agentId -> connectionId

  constructor(config: ServerConfig) {
    this.config = config;
  }

  async start(): Promise<void> {
    logger.info('Starting MCP Server', {
      port: this.config.port,
      authEnabled: !!this.config.auth?.jwtSecret,
    });

    // Initialize protocol handler
    this.protocolHandler = new ProtocolHandler();
    logger.debug('Protocol handler initialized');

    // Initialize registry
    this.registry = new ToolRegistry();
    logger.debug('Registry initialized');

    // Initialize transport
    this.transport = new WebSocketTransport({
      port: this.config.port,
      auth: {
        enabled: !!this.config.auth?.jwtSecret,
        sharedSecret: this.config.auth?.jwtSecret,
      },
    });
    this.transport.setProtocolHandler(this.protocolHandler);

    // Initialize invoker with callback to get agent connections
    this.invoker = new ToolInvoker(
      this.registry,
      (agentId: string) => {
        // Return a wrapper that can send messages to the agent connection
        const agentConnectionId = this.agentConnections.get(agentId);
        if (!agentConnectionId) {
          return undefined;
        }
        return {
          sendMessage: async (message: any) => {
            const conn = this.transport!.getConnections().find((c) => c.id === agentConnectionId);
            if (conn && conn.ws.readyState === WebSocket.OPEN) {
              conn.ws.send(JSON.stringify(message));
            }
          },
        };
      }
    );
    logger.debug('Registry and invoker initialized');

    // Set response handler on protocol handler to route tool invocation responses
    this.protocolHandler.setResponseHandler((invocationId: string, response: any) => {
      this.invoker!.handleInvocationResponse(invocationId, response);
    });

    // Initialize server handlers
    this.handlers = new ServerHandlers(this.registry, this.transport, this.agentConnections);

    // Register JSON-RPC method handlers
    this.protocolHandler.registerHandler('tools/list', async (method, params) => {
      return this.handlers!.handleToolsList();
    });

    this.protocolHandler.registerHandler('tools/register', async (method, params) => {
      return this.handlers!.handleToolsRegister(params);
    });

    this.protocolHandler.registerHandler('agents/list', async (method, params) => {
      return this.handlers!.handleAgentsList();
    });

    this.protocolHandler.registerHandler('tools/invoke', async (method, params: any) => {
      logger.info('🔍 TRACE: Received tools/invoke request', { 
        toolName: params?.toolName, 
        hasArguments: !!params?.arguments,
        params: JSON.stringify(params).substring(0, 200)
      });
      const { toolName, arguments: args } = params;
      logger.info('🔍 TRACE: Invoking tool via invoker', { toolName });
      const result = await this.invoker!.invoke({
        toolName,
        arguments: args || {},
      });
      logger.info('🔍 TRACE: Tool invocation completed', { 
        toolName, 
        success: !!result,
        resultKeys: result ? Object.keys(result) : []
      });
      return result;
    });

    logger.debug('Method handlers registered', {
      methods: ['tools/list', 'tools/register', 'agents/list', 'tools/invoke'],
    });

    await this.transport.start();
    logger.info('WebSocket transport started', { port: this.config.port });

    logger.info('MCP Server started successfully', { port: this.config.port });
  }

  async stop(): Promise<void> {
    logger.info('Stopping MCP Server');

    if (this.transport) {
      await this.transport.stop();
      logger.debug('WebSocket transport stopped');
    }

    logger.info('MCP Server stopped');
  }

  getRegistry(): ToolRegistry | undefined {
    return this.registry;
  }

  getTransport(): WebSocketTransport | undefined {
    return this.transport;
  }
}
