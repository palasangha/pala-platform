import { useState, useEffect, useRef, useCallback } from 'react';

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

export function useWebSocket(url?: string) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messageHandlerRef = useRef<Map<number, (response: unknown) => void>>(new Map());
  const messageIdRef = useRef(0);
  const log = useCallback((message: string, payload?: unknown) => {
    console.log(`[WS] ${message}`, payload ?? '');
  }, []);

  // Default URL if not provided
  const [wsUrl, setWsUrl] = useState(url || '');

  useEffect(() => {
    if (!url && typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      setWsUrl(`${protocol}//${host}:3010`);
    }
  }, [url]);

  const effectiveUrl = url || wsUrl;

  useEffect(() => {
    if (!effectiveUrl) {
      setConnected(false);
      return;
    }

    const ws = new WebSocket(effectiveUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      log('connected', { url: effectiveUrl });
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      log('recv raw', event.data);
      try {
        const message = JSON.parse(event.data);
        log('recv parsed', { id: message.id, method: message.method, keys: Object.keys(message || {}) });
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
      log('error', event);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      log('disconnected', { url: effectiveUrl });
      setConnected(false);
    };

    wsRef.current = ws;

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [effectiveUrl]);

  const send = useCallback((method: string, params?: unknown): Promise<unknown> => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.log('[WS] send blocked: socket not connected', { method, params });
        reject(new Error('WebSocket not connected'));
        return;
      }

      const id = ++messageIdRef.current;
      const message = { jsonrpc: '2.0', method, params, id };
      console.log('[WS] send', { id, method, params });

      messageHandlerRef.current.set(id, (response: unknown) => {
        const resp = response as any;
        console.log('[WS] response received', { id, method, hasError: Boolean(resp?.error), keys: Object.keys(resp || {}) });
        if (resp.error) {
          console.log('[WS] response error', { id, method, error: resp.error });
          reject(new Error(resp.error.message));
        } else {
          resolve(resp.result);
        }
      });

      try {
        wsRef.current.send(JSON.stringify(message));
        // Timeout after 1800 seconds (30 minutes) for long-running operations like OCR with model loading
        setTimeout(() => {
          if (messageHandlerRef.current.has(id)) {
            messageHandlerRef.current.delete(id);
            console.log('[WS] request timeout', { id, method });
            reject(new Error('Request timeout'));
          }
        }, 1800000);
      } catch (err) {
        console.log('[WS] send exception', { id, method, err });
        reject(err);
      }
    });
  }, []);

  return { connected, error, send, client: wsRef.current };
}
