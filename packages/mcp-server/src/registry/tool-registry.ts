/**
 * Tool Registry - Manages tool registration and discovery
 * 
 * Responsibilities:
 * - Register tools from agents with validation
 * - Discover available tools by name or capability
 * - Route tool invocations to appropriate agents
 * - Track tool metadata and schemas
 */

import { EventEmitter } from 'events';
import { z } from 'zod';

/**
 * JSON Schema for tool input validation
 */
export const JSONSchemaSchema = z.object({
  type: z.string(),
  properties: z.record(z.any()).optional(),
  required: z.array(z.string()).optional(),
  additionalProperties: z.boolean().optional(),
});

export type JSONSchema = z.infer<typeof JSONSchemaSchema>;

/**
 * Tool definition schema
 */
export const ToolDefinitionSchema = z.object({
  name: z.string().min(1).regex(/^[a-zA-Z0-9_-]+$/),
  description: z.string().min(1),
  inputSchema: JSONSchemaSchema,
  agentId: z.string().min(1),
  metadata: z.record(z.any()).optional(),
});

export type ToolDefinition = z.infer<typeof ToolDefinitionSchema>;

/**
 * Tool invocation request
 */
export interface ToolInvocationRequest {
  toolName: string;
  arguments: Record<string, any>;
  requestId?: string;
  traceId?: string;
}

/**
 * Tool invocation result
 */
export interface ToolInvocationResult {
  success: boolean;
  result?: any;
  error?: string;
  agentId: string;
  toolName: string;
  traceId?: string;
}

/**
 * Registry events
 */
export interface ToolRegistryEvents {
  'tool:registered': (tool: ToolDefinition) => void;
  'tool:unregistered': (toolName: string, agentId: string) => void;
  'tool:invoked': (request: ToolInvocationRequest, result: ToolInvocationResult) => void;
  error: (error: Error) => void;
}

/**
 * Tool Registry manages tool registration and routing
 */
export class ToolRegistry extends EventEmitter {
  private tools: Map<string, ToolDefinition> = new Map();
  private agentTools: Map<string, Set<string>> = new Map();

  /**
   * Register a tool from an agent
   */
  register(tool: ToolDefinition): void {
    // Validate tool definition
    const validated = ToolDefinitionSchema.parse(tool);

    // Check for duplicate tool names
    if (this.tools.has(validated.name)) {
      throw new Error(`Tool '${validated.name}' is already registered`);
    }

    // Store tool
    this.tools.set(validated.name, validated);

    // Track agent's tools
    if (!this.agentTools.has(validated.agentId)) {
      this.agentTools.set(validated.agentId, new Set());
    }
    this.agentTools.get(validated.agentId)!.add(validated.name);

    this.emit('tool:registered', validated);
  }

  /**
   * Unregister a tool by name
   */
  unregister(toolName: string): void {
    const tool = this.tools.get(toolName);
    if (!tool) {
      throw new Error(`Tool '${toolName}' not found`);
    }

    // Remove from agent's tool set
    const agentToolSet = this.agentTools.get(tool.agentId);
    if (agentToolSet) {
      agentToolSet.delete(toolName);
      if (agentToolSet.size === 0) {
        this.agentTools.delete(tool.agentId);
      }
    }

    this.tools.delete(toolName);
    this.emit('tool:unregistered', toolName, tool.agentId);
  }

  /**
   * Unregister all tools for an agent
   */
  unregisterAgent(agentId: string): void {
    const toolNames = this.agentTools.get(agentId);
    if (!toolNames) {
      return;
    }

    // Unregister each tool
    for (const toolName of toolNames) {
      this.tools.delete(toolName);
      this.emit('tool:unregistered', toolName, agentId);
    }

    this.agentTools.delete(agentId);
  }

  /**
   * Get tool definition by name
   */
  getTool(toolName: string): ToolDefinition | undefined {
    return this.tools.get(toolName);
  }

  /**
   * List all registered tools
   */
  listTools(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  /**
   * List tools for a specific agent
   */
  listAgentTools(agentId: string): ToolDefinition[] {
    const toolNames = this.agentTools.get(agentId);
    if (!toolNames) {
      return [];
    }

    return Array.from(toolNames)
      .map((name) => this.tools.get(name))
      .filter((tool): tool is ToolDefinition => tool !== undefined);
  }

  /**
   * Search tools by description keyword
   */
  searchTools(keyword: string): ToolDefinition[] {
    const lowerKeyword = keyword.toLowerCase();
    return Array.from(this.tools.values()).filter(
      (tool) =>
        tool.name.toLowerCase().includes(lowerKeyword) ||
        tool.description.toLowerCase().includes(lowerKeyword)
    );
  }

  /**
   * Validate tool invocation arguments against schema
   */
  validateArguments(toolName: string, args: Record<string, any>): void {
    const tool = this.tools.get(toolName);
    if (!tool) {
      throw new Error(`Tool '${toolName}' not found`);
    }

    const schema = tool.inputSchema;

    // Check required fields
    if (schema.required) {
      for (const field of schema.required) {
        if (!(field in args)) {
          throw new Error(`Missing required argument '${field}' for tool '${toolName}'`);
        }
      }
    }

    // Check for unexpected fields if additionalProperties is false
    if (schema.additionalProperties === false && schema.properties) {
      const allowedFields = Object.keys(schema.properties);
      for (const field of Object.keys(args)) {
        if (!allowedFields.includes(field)) {
          throw new Error(`Unexpected argument '${field}' for tool '${toolName}'`);
        }
      }
    }

    // Type validation would go here (checking against schema.properties)
    // For now, we do basic presence validation
  }

  /**
   * Get agent ID for a tool (for routing invocations)
   */
  getToolAgent(toolName: string): string | undefined {
    return this.tools.get(toolName)?.agentId;
  }

  /**
   * Get total number of registered tools
   */
  getToolCount(): number {
    return this.tools.size;
  }

  /**
   * Get total number of agents with registered tools
   */
  getAgentCount(): number {
    return this.agentTools.size;
  }

  /**
   * Clear all registered tools (for testing)
   */
  clear(): void {
    this.tools.clear();
    this.agentTools.clear();
  }
}
