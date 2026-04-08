/**
 * Tests for Tool Registry
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { ToolRegistry, ToolDefinition } from '../../src/registry/tool-registry';

describe('ToolRegistry', () => {
  let registry: ToolRegistry;

  const sampleTool: ToolDefinition = {
    name: 'test-tool',
    description: 'A test tool for unit testing',
    agentId: 'agent-1',
    inputSchema: {
      type: 'object',
      properties: {
        input: { type: 'string' },
      },
      required: ['input'],
    },
  };

  beforeEach(() => {
    registry = new ToolRegistry();
  });

  describe('registration', () => {
    it('should register a valid tool', () => {
      registry.register(sampleTool);

      const tool = registry.getTool('test-tool');
      expect(tool).toBeDefined();
      expect(tool?.name).toBe('test-tool');
      expect(tool?.agentId).toBe('agent-1');
    });

    it('should reject invalid tool names', () => {
      const invalidTool = { ...sampleTool, name: 'invalid name!' };
      expect(() => registry.register(invalidTool)).toThrow();
    });

    it('should reject empty tool names', () => {
      const invalidTool = { ...sampleTool, name: '' };
      expect(() => registry.register(invalidTool)).toThrow();
    });

    it('should reject duplicate tool names', () => {
      registry.register(sampleTool);
      expect(() => registry.register(sampleTool)).toThrow("Tool 'test-tool' is already registered");
    });

    it('should emit tool:registered event', () => {
      let emittedTool: ToolDefinition | undefined;
      registry.on('tool:registered', (tool) => {
        emittedTool = tool;
      });

      registry.register(sampleTool);

      expect(emittedTool).toBeDefined();
      expect(emittedTool?.name).toBe('test-tool');
    });

    it('should track multiple tools per agent', () => {
      const tool1 = { ...sampleTool, name: 'tool-1' };
      const tool2 = { ...sampleTool, name: 'tool-2' };

      registry.register(tool1);
      registry.register(tool2);

      const agentTools = registry.listAgentTools('agent-1');
      expect(agentTools).toHaveLength(2);
      expect(agentTools.map((t) => t.name)).toContain('tool-1');
      expect(agentTools.map((t) => t.name)).toContain('tool-2');
    });
  });

  describe('unregistration', () => {
    beforeEach(() => {
      registry.register(sampleTool);
    });

    it('should unregister a tool by name', () => {
      registry.unregister('test-tool');

      const tool = registry.getTool('test-tool');
      expect(tool).toBeUndefined();
    });

    it('should throw when unregistering non-existent tool', () => {
      expect(() => registry.unregister('non-existent')).toThrow("Tool 'non-existent' not found");
    });

    it('should emit tool:unregistered event', () => {
      let emittedToolName: string | undefined;
      let emittedAgentId: string | undefined;

      registry.on('tool:unregistered', (toolName, agentId) => {
        emittedToolName = toolName;
        emittedAgentId = agentId;
      });

      registry.unregister('test-tool');

      expect(emittedToolName).toBe('test-tool');
      expect(emittedAgentId).toBe('agent-1');
    });

    it('should unregister all tools for an agent', () => {
      const tool2 = { ...sampleTool, name: 'tool-2' };
      registry.register(tool2);

      registry.unregisterAgent('agent-1');

      expect(registry.getTool('test-tool')).toBeUndefined();
      expect(registry.getTool('tool-2')).toBeUndefined();
      expect(registry.listAgentTools('agent-1')).toHaveLength(0);
    });

    it('should handle unregistering agent with no tools', () => {
      expect(() => registry.unregisterAgent('non-existent')).not.toThrow();
    });
  });

  describe('discovery', () => {
    beforeEach(() => {
      registry.register(sampleTool);
      registry.register({
        name: 'search-tool',
        description: 'Search documents and files',
        agentId: 'agent-2',
        inputSchema: {
          type: 'object',
          properties: { query: { type: 'string' } },
        },
      });
      registry.register({
        name: 'file-tool',
        description: 'Read and write files',
        agentId: 'agent-2',
        inputSchema: {
          type: 'object',
          properties: { path: { type: 'string' } },
        },
      });
    });

    it('should list all tools', () => {
      const tools = registry.listTools();
      expect(tools).toHaveLength(3);
      expect(tools.map((t) => t.name)).toContain('test-tool');
      expect(tools.map((t) => t.name)).toContain('search-tool');
      expect(tools.map((t) => t.name)).toContain('file-tool');
    });

    it('should list tools for specific agent', () => {
      const agent2Tools = registry.listAgentTools('agent-2');
      expect(agent2Tools).toHaveLength(2);
      expect(agent2Tools.map((t) => t.name)).toContain('search-tool');
      expect(agent2Tools.map((t) => t.name)).toContain('file-tool');
    });

    it('should search tools by name keyword', () => {
      const results = registry.searchTools('file-tool');
      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('file-tool');
    });

    it('should search tools by description keyword', () => {
      const results = registry.searchTools('search');
      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('search-tool');
    });

    it('should return empty array for no matches', () => {
      const results = registry.searchTools('nonexistent');
      expect(results).toHaveLength(0);
    });

    it('should get tool agent ID', () => {
      const agentId = registry.getToolAgent('search-tool');
      expect(agentId).toBe('agent-2');
    });

    it('should return undefined for non-existent tool agent', () => {
      const agentId = registry.getToolAgent('non-existent');
      expect(agentId).toBeUndefined();
    });
  });

  describe('argument validation', () => {
    beforeEach(() => {
      registry.register({
        name: 'strict-tool',
        description: 'Tool with strict schema',
        agentId: 'agent-1',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            age: { type: 'number' },
          },
          required: ['name'],
          additionalProperties: false,
        },
      });
    });

    it('should validate required arguments', () => {
      expect(() => registry.validateArguments('strict-tool', { name: 'John' })).not.toThrow();
    });

    it('should reject missing required arguments', () => {
      expect(() => registry.validateArguments('strict-tool', { age: 25 })).toThrow(
        "Missing required argument 'name'"
      );
    });

    it('should reject unexpected arguments when additionalProperties is false', () => {
      expect(() =>
        registry.validateArguments('strict-tool', { name: 'John', extra: 'field' })
      ).toThrow("Unexpected argument 'extra'");
    });

    it('should allow additional arguments when additionalProperties is not false', () => {
      registry.register({
        name: 'flexible-tool',
        description: 'Tool with flexible schema',
        agentId: 'agent-1',
        inputSchema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
          },
        },
      });

      expect(() =>
        registry.validateArguments('flexible-tool', { name: 'John', extra: 'field' })
      ).not.toThrow();
    });

    it('should throw for non-existent tool', () => {
      expect(() => registry.validateArguments('non-existent', {})).toThrow(
        "Tool 'non-existent' not found"
      );
    });
  });

  describe('statistics', () => {
    it('should count registered tools', () => {
      expect(registry.getToolCount()).toBe(0);

      registry.register(sampleTool);
      expect(registry.getToolCount()).toBe(1);

      registry.register({ ...sampleTool, name: 'tool-2' });
      expect(registry.getToolCount()).toBe(2);
    });

    it('should count agents with registered tools', () => {
      expect(registry.getAgentCount()).toBe(0);

      registry.register(sampleTool);
      expect(registry.getAgentCount()).toBe(1);

      registry.register({ ...sampleTool, name: 'tool-2', agentId: 'agent-2' });
      expect(registry.getAgentCount()).toBe(2);

      // Same agent shouldn't increase count
      registry.register({ ...sampleTool, name: 'tool-3', agentId: 'agent-1' });
      expect(registry.getAgentCount()).toBe(2);
    });
  });

  describe('clear', () => {
    it('should clear all tools', () => {
      registry.register(sampleTool);
      registry.register({ ...sampleTool, name: 'tool-2' });

      registry.clear();

      expect(registry.getToolCount()).toBe(0);
      expect(registry.getAgentCount()).toBe(0);
      expect(registry.listTools()).toHaveLength(0);
    });
  });
});
