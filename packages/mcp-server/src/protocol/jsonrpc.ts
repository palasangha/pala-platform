/**
 * JSON-RPC 2.0 Protocol Implementation
 * Handles message validation, error responses, and protocol compliance
 */

import { z } from 'zod';
import type { JSONRPCRequest, JSONRPCResponse, JSONRPCError } from '../types';

// JSON-RPC 2.0 Error Codes
export const ErrorCodes = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
} as const;

// Zod schemas for validation
const JSONRPCRequestSchema = z.object({
  jsonrpc: z.literal('2.0'),
  id: z.union([z.string(), z.number()]),
  method: z.string(),
  params: z.unknown().optional(),
});

const JSONRPCNotificationSchema = z.object({
  jsonrpc: z.literal('2.0'),
  method: z.string(),
  params: z.unknown().optional(),
});

export class JSONRPCProtocol {
  /**
   * Validate incoming JSON-RPC request
   */
  validateRequest(data: unknown): { valid: true; request: JSONRPCRequest } | { valid: false; error: JSONRPCError } {
    try {
      const parsed = JSONRPCRequestSchema.parse(data);
      return { valid: true, request: parsed as JSONRPCRequest };
    } catch (error) {
      return {
        valid: false,
        error: {
          code: ErrorCodes.INVALID_REQUEST,
          message: 'Invalid Request',
          data: error instanceof Error ? error.message : 'Unknown validation error',
        },
      };
    }
  }

  /**
   * Validate notification (no id field)
   */
  validateNotification(data: unknown): boolean {
    try {
      JSONRPCNotificationSchema.parse(data);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Create success response
   */
  createResponse(id: string | number, result: unknown): JSONRPCResponse {
    return {
      jsonrpc: '2.0',
      id,
      result,
    };
  }

  /**
   * Create error response
   */
  createErrorResponse(id: string | number | null, code: number, message: string, data?: unknown): JSONRPCResponse {
    return {
      jsonrpc: '2.0',
      id: id ?? 'error',
      error: {
        code,
        message,
        data,
      },
    };
  }

  /**
   * Parse raw message string
   */
  parseMessage(message: string): { success: true; data: unknown } | { success: false; error: JSONRPCError } {
    try {
      const data = JSON.parse(message);
      return { success: true, data };
    } catch (error) {
      return {
        success: false,
        error: {
          code: ErrorCodes.PARSE_ERROR,
          message: 'Parse error',
          data: error instanceof Error ? error.message : 'Invalid JSON',
        },
      };
    }
  }

  /**
   * Stringify response for transmission
   */
  stringifyResponse(response: JSONRPCResponse): string {
    return JSON.stringify(response);
  }
}
