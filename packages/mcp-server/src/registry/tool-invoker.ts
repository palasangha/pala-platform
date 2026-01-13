/**
 * Tool Invoker - Handles tool invocation routing and execution
 * 
 * Responsibilities:
 * - Route tool invocations to appropriate agents
 * - Handle invocation lifecycle (request -> response)
 * - Emit invocation events for logging/tracing
 */

import { EventEmitter } from 'events';
import { ToolRegistry, ToolInvocationRequest, ToolInvocationResult } from './tool-registry';
import { ensureTraceId } from '../tracing';

/**
 * Agent connection interface (implemented by transport layer)
 */
export interface AgentConnection {
  sendMessage(message: any): Promise<void>;
}

/**
 * Tool invoker events
 */
export interface ToolInvokerEvents {
  'invocation:started': (request: ToolInvocationRequest) => void;
  'invocation:completed': (result: ToolInvocationResult) => void;
  'invocation:failed': (request: ToolInvocationRequest, error: Error) => void;
}

/**
 * Tool Invoker routes and executes tool invocations
 */
export class ToolInvoker extends EventEmitter {
  private pendingInvocations: Map<string, (result: any) => void> = new Map();
  private invocationTimeout: number = 30000; // 30 seconds default

  constructor(
    private registry: ToolRegistry,
    private getAgentConnection: (agentId: string) => AgentConnection | undefined
  ) {
    super();
  }

  /**
   * Invoke a tool by name with arguments
   */
  async invoke(request: ToolInvocationRequest): Promise<ToolInvocationResult> {
    const { toolName, arguments: args, requestId } = request;
    const traceId = ensureTraceId(request.traceId);

    // Validate tool exists
    const tool = this.registry.getTool(toolName);
    if (!tool) {
      const error = `Tool '${toolName}' not found`;
      this.emit('invocation:failed', { ...request, traceId }, new Error(error));
      return {
        success: false,
        error,
        agentId: '',
        toolName,
        traceId,
      };
    }

    // Validate arguments against schema
    try {
      this.registry.validateArguments(toolName, args);
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      this.emit('invocation:failed', { ...request, traceId }, err as Error);
      return {
        success: false,
        error,
        agentId: tool.agentId,
        toolName,
        traceId,
      };
    }

    // Get agent connection
    const connection = this.getAgentConnection(tool.agentId);
    if (!connection) {
      const error = `Agent '${tool.agentId}' not connected`;
      this.emit('invocation:failed', { ...request, traceId }, new Error(error));
      return {
        success: false,
        error,
        agentId: tool.agentId,
        toolName,
        traceId,
      };
    }

    // Emit started event
    this.emit('invocation:started', { ...request, traceId });

    // Generate invocation ID
    const invocationId = requestId || this.generateInvocationId();

    try {
      // Send invocation request to agent
      const result = await this.sendInvocationToAgent(
        connection,
        invocationId,
        toolName,
        args,
        traceId
      );

      const successResult: ToolInvocationResult = {
        success: true,
        result,
        agentId: tool.agentId,
        toolName,
        traceId,
      };

      this.emit('invocation:completed', successResult);
      return successResult;
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      const errorResult: ToolInvocationResult = {
        success: false,
        error,
        agentId: tool.agentId,
        toolName,
        traceId,
      };

      this.emit('invocation:failed', { ...request, traceId }, err as Error);
      return errorResult;
    }
  }

  /**
   * Send invocation request to agent and wait for response
   */
  private async sendInvocationToAgent(
    connection: AgentConnection,
    invocationId: string,
    toolName: string,
    args: Record<string, any>,
    traceId: string
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      // Set timeout
      const timeout = setTimeout(() => {
        this.pendingInvocations.delete(invocationId);
        reject(new Error(`Tool invocation timed out after ${this.invocationTimeout}ms`));
      }, this.invocationTimeout);

      // Store resolver
      this.pendingInvocations.set(invocationId, (result) => {
        clearTimeout(timeout);
        if (result.error) {
          reject(new Error(result.error));
        } else {
          resolve(result.data);
        }
      });

      // Send message to agent
      connection
        .sendMessage({
          jsonrpc: '2.0',
          method: 'tools/invoke',
          params: {
            name: toolName,
            arguments: args,
          },
          id: invocationId,
          traceId,
        })
        .catch((err) => {
          clearTimeout(timeout);
          this.pendingInvocations.delete(invocationId);
          reject(err);
        });
    });
  }

  /**
   * Handle invocation response from agent
   */
  handleInvocationResponse(invocationId: string, response: any): void {
    const resolver = this.pendingInvocations.get(invocationId);
    if (!resolver) {
      // Response for unknown invocation - might be timeout or duplicate
      return;
    }

    this.pendingInvocations.delete(invocationId);
    resolver(response);
  }

  /**
   * Set invocation timeout in milliseconds
   */
  setInvocationTimeout(timeout: number): void {
    if (timeout <= 0) {
      throw new Error('Invocation timeout must be greater than 0');
    }
    this.invocationTimeout = timeout;
  }

  /**
   * Get current invocation timeout
   */
  getInvocationTimeout(): number {
    return this.invocationTimeout;
  }

  /**
   * Get count of pending invocations
   */
  getPendingCount(): number {
    return this.pendingInvocations.size;
  }

  /**
   * Generate unique invocation ID
   */
  private generateInvocationId(): string {
    return `inv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Clear all pending invocations (for testing/cleanup)
   */
  clearPending(): void {
    // Reject all pending invocations
    for (const [id, resolver] of this.pendingInvocations) {
      resolver({ error: 'Invocation cancelled' });
    }
    this.pendingInvocations.clear();
  }
}
