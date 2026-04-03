import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export type ToolField = {
  name: string;
  type: string;
  required?: boolean;
  description: string;
  possibleValues?: string[];
  defaultValue?: string;
};

export type ToolDef = {
  name: string;
  description: string;
  placeholder?: string;
  examples?: Array<{ label: string; input: string }>;
  schemaFields: ToolField[];
};

export type AgentDef = {
  id: string;
  name: string;
  tools: ToolDef[];
};

export function useTools() {
  const [agents, setAgents] = useState<AgentDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { send } = useWebSocket();

  useEffect(() => {
    const fetchTools = async () => {
      try {
        setLoading(true);
        setError(null);
        const result: any = await send('tools/list', {});
        
        if (result && result.tools) {
          // Group tools by agentId
          const agentMap = new Map<string, ToolDef[]>();
          
          result.tools.forEach((tool: any) => {
            const agentId = tool.agentId || 'unknown';
            if (!agentMap.has(agentId)) {
              agentMap.set(agentId, []);
            }
            
            const toolDef: ToolDef = {
              name: tool.name,
              description: tool.description || '',
              placeholder: `Enter JSON for ${tool.name}`,
              examples: [
                { 
                  label: 'Example', 
                  input: JSON.stringify(
                    tool.inputSchema?.properties 
                      ? Object.keys(tool.inputSchema.properties).reduce((acc: any, key) => {
                          acc[key] = 'value';
                          return acc;
                        }, {})
                      : {}
                  ) 
                }
              ],
              schemaFields: tool.inputSchema?.properties 
                ? Object.entries(tool.inputSchema.properties).map(([key, schema]: [string, any]) => ({
                    name: key,
                    type: schema.type || 'string',
                    required: tool.inputSchema.required?.includes(key),
                    description: schema.description || '',
                  }))
                : []
            };
            
            agentMap.get(agentId)!.push(toolDef);
          });
          
          // Convert map to agent list
          const agentList: AgentDef[] = Array.from(agentMap.entries()).map(([agentId, tools]) => ({
            id: agentId,
            name: agentId.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
            tools
          }));
          
          setAgents(agentList);
        }
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Failed to fetch tools';
        setError(errMsg);
        console.error('Failed to fetch tools:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchTools();
  }, [send]);

  return { agents, loading, error };
}
