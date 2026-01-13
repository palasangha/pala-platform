/**
 * Server-side RPC method handlers for tool registry and agent discovery
 */

import { ToolRegistry } from './registry/tool-registry';
import { WebSocketTransport, Connection } from './transport/websocket';

export class ServerHandlers {
  constructor(
    private registry: ToolRegistry,
    private transport: WebSocketTransport
  ) {}

  /**
   * Handle tools/register request from agent
   * Expects params: { tools: ToolDefinition[] }
   */
  async handleToolsRegister(params: any): Promise<{ registered: number }> {
    if (!params || !Array.isArray(params.tools)) {
      throw new Error('Invalid tools/register: expected { tools: [...] }');
    }

    let count = 0;
    for (const tool of params.tools) {
      try {
        this.registry.register(tool);
        count++;
      } catch (err: any) {
        // Log but continue registering other tools
        console.warn(`Failed to register tool ${tool.name}:`, err.message);
      }
    }

    return { registered: count };
  }

  /**
   * Handle tools/list request
   * Returns all registered tools
   */
  async handleToolsList(): Promise<{ tools: any[] }> {
    const tools = this.registry.listTools();
    return { tools };
  }

  /**
   * Handle agents/list request
   * Returns connected agents with metadata
   */
  async handleAgentsList(): Promise<{ agents: any[] }> {
    const connections = this.transport.getConnections();
    const agents = connections
      .filter((conn) => conn.metadata?.principalId)
      .map((conn) => ({
        id: conn.id,
        principalId: conn.metadata?.principalId,
        tools: this.registry.listAgentTools(conn.metadata?.principalId || ''),
      }));

    return { agents };
  }
}
