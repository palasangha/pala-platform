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

const logger = new Logger({ name: 'MCPServer' });

export class MCPServer {
  private config: ServerConfig;
  private transport?: WebSocketTransport;
  private protocolHandler?: ProtocolHandler;
  private registry?: ToolRegistry;
  private invoker?: ToolInvoker;
  private handlers?: ServerHandlers;

  constructor(config: ServerConfig) {
    this.config = config;
  }

  async start(): Promise<void> {
    logger.info('Starting MCP Server', {
      port: this.config.port,
      authEnabled: !!this.config.authSecret,
    });

    // Initialize protocol handler
    this.protocolHandler = new ProtocolHandler();
    logger.debug('Protocol handler initialized');

    // Initialize registry and invoker
    this.registry = new ToolRegistry();
    this.invoker = new ToolInvoker(this.registry);
    logger.debug('Registry and invoker initialized');

    // Initialize server handlers
    this.handlers = new ServerHandlers(this.registry, this.transport!);

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
      const { toolName, agentId, arguments: args } = params;
      const result = await this.invoker!.invoke({
        toolName,
        agentId,
        arguments: args || {},
      });
      return result;
    });

    logger.debug('Method handlers registered', {
      methods: ['tools/list', 'tools/register', 'agents/list', 'tools/invoke'],
    });

    // Initialize transport
    this.transport = new WebSocketTransport({
      port: this.config.port,
      authSecret: this.config.authSecret,
    });
    this.transport.setProtocolHandler(this.protocolHandler);

    // Update handlers with transport (needs to be set after transport is created)
    if (this.handlers) {
      this.handlers = new ServerHandlers(this.registry, this.transport);
    }

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
