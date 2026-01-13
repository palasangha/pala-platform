/**
 * Core type definitions for MCP Server
 */

export interface ServerConfig {
  port: number;
  host?: string;
  tls?: {
    enabled: boolean;
    cert?: string;
    key?: string;
  };
  auth?: {
    jwtSecret?: string;
    agentApiKeys?: string[];
  };
  logging?: {
    level: 'debug' | 'info' | 'warn' | 'error';
    pretty?: boolean;
  };
}

export interface JSONRPCRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: unknown;
}

export interface JSONRPCResponse {
  jsonrpc: '2.0';
  id: string | number;
  result?: unknown;
  error?: JSONRPCError;
}

export interface JSONRPCError {
  code: number;
  message: string;
  data?: unknown;
}
