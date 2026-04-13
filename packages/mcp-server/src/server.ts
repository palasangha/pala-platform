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
import { StorageTool, getStorageTools } from './storage/storage-tool';

const logger = new Logger({ name: 'MCPServer' });

export class MCPServer {
  private config: ServerConfig;
  private transport?: WebSocketTransport;
  private protocolHandler?: ProtocolHandler;
  private registry?: ToolRegistry;
  private invoker?: ToolInvoker;
  private handlers?: ServerHandlers;
  private agentConnections: Map<string, string> = new Map(); // agentId -> connectionId
  private storageTool?: StorageTool;

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
    const transportConfig: any = {
      port: this.config.port,
      host: this.config.host || '0.0.0.0',
      auth: {
        enabled: !!this.config.auth?.jwtSecret,
        sharedSecret: this.config.auth?.jwtSecret,
      },
    };

    // Only add ping settings if they're defined
    if (this.config.transport?.pingInterval !== undefined) {
      transportConfig.pingInterval = this.config.transport.pingInterval;
    }
    if (this.config.transport?.pingTimeout !== undefined) {
      transportConfig.pingTimeout = this.config.transport.pingTimeout;
    }

    this.transport = new WebSocketTransport(transportConfig);
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

    // Initialize storage tool
    this.storageTool = new StorageTool();
    logger.debug('Storage tool initialized');

    // Register storage tools as a system provider
    const storageTools = getStorageTools();
    for (const tool of storageTools) {
      this.registry.register(tool);
    }
    logger.debug(`Storage provider registered with ${storageTools.length} tools`);

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
      // Support both 'name' and 'toolName' for backward compatibility
      const toolName = params.name || params.toolName;
      const args = params.arguments || params.args || {};
      
      // Handle storage tools directly
      if (toolName === 'store-content') {
        const result = await this.storageTool!.storeContent(args);
        return result;
      } else if (toolName === 'retrieve-content') {
        const result = await this.storageTool!.retrieveContent(args.content_id);
        return result;
      } else if (toolName === 'list-content') {
        const result = await this.storageTool!.listContent();
        return result;
      } else if (toolName === 'list-backends') {
        const result = await this.storageTool!.listBackends();
        return result;
      }
      
      // Handle other agent tools
      const result = await this.invoker!.invoke({
        toolName,
        arguments: args,
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
