/**
 * Server-side RPC method handlers for tool registry and agent discovery
 */

import { ToolRegistry } from './registry/tool-registry';
import { WebSocketTransport } from './transport/websocket';
import { getCurrentConnectionId } from './transport/websocket';

export class ServerHandlers {
  constructor(
    private registry: ToolRegistry,
    private transport: WebSocketTransport,
    private agentConnections?: Map<string, string>
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
    let firstAgentId = '';
    for (const tool of params.tools) {
      try {
        this.registry.register(tool);
        count++;
        if (!firstAgentId && tool.agentId) {
          firstAgentId = tool.agentId;
        }
      } catch (err: any) {
        // Log but continue registering other tools
        console.warn(`Failed to register tool ${tool.name}:`, err.message);
      }
    }

    // Track the agent connection using current connection context
    if (firstAgentId && this.agentConnections) {
      const connectionId = getCurrentConnectionId();
      if (connectionId) {
        this.agentConnections.set(firstAgentId, connectionId);
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
   * Returns connected agents with their tools
   */
  async handleAgentsList(): Promise<{ agents: any[] }> {
    // Get all unique agent IDs from registered tools
    const tools = this.registry.listTools();
    const agentIds = new Set<string>();
    
    for (const tool of tools) {
      if (tool.agentId) {
        agentIds.add(tool.agentId);
      }
    }

    // Return agents with their tools
    const agents = Array.from(agentIds).map((agentId) => ({
      id: agentId,
      name: agentId,
      tools: this.registry.listAgentTools(agentId),
    }));

    return { agents };
  }
}
