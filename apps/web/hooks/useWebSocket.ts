import { useState, useEffect, useRef } from 'react';

interface ToolDefinition {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  agentId: string;
}

interface Agent {
  id: string;
  tools: ToolDefinition[];
}

export function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messageHandlerRef = useRef<Map<number, (response: unknown) => void>>(new Map());
  const messageIdRef = useRef(0);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.id && messageHandlerRef.current.has(message.id)) {
          const handler = messageHandlerRef.current.get(message.id)!;
          handler(message);
          messageHandlerRef.current.delete(message.id);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const send = (method: string, params?: unknown): Promise<unknown> => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const id = ++messageIdRef.current;
      const message = { jsonrpc: '2.0', method, params, id };

      messageHandlerRef.current.set(id, (response: unknown) => {
        const resp = response as any;
        if (resp.error) {
          reject(new Error(resp.error.message));
        } else {
          resolve(resp.result);
        }
      });

      try {
        wsRef.current.send(JSON.stringify(message));
        // Timeout after 10 seconds
        setTimeout(() => {
          if (messageHandlerRef.current.has(id)) {
            messageHandlerRef.current.delete(id);
            reject(new Error('Request timeout'));
          }
        }, 10000);
      } catch (err) {
        reject(err);
      }
    });
  };

  return { connected, error, send };
}
