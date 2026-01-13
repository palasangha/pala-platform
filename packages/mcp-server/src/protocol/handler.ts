/**
 * Protocol Handler
 * Coordinates message handling, method routing, and response generation
 */

import { JSONRPCProtocol, ErrorCodes } from './jsonrpc';
import type { JSONRPCRequest, JSONRPCResponse } from '../types';

export type MessageHandler = (method: string, params: unknown) => Promise<unknown>;
export type ResponseHandler = (invocationId: string, response: any) => void;

export class ProtocolHandler {
  private protocol: JSONRPCProtocol;
  private handlers: Map<string, MessageHandler>;
  private responseHandler?: ResponseHandler;

  constructor() {
    this.protocol = new JSONRPCProtocol();
    this.handlers = new Map();
  }

  /**
   * Register a response handler for tool invocation responses
   */
  setResponseHandler(handler: ResponseHandler): void {
    this.responseHandler = handler;
  }

  /**
   * Register a method handler
   */
  registerHandler(method: string, handler: MessageHandler): void {
    this.handlers.set(method, handler);
  }

  /**
   * Unregister a method handler
   */
  unregisterHandler(method: string): void {
    this.handlers.delete(method);
  }

  /**
   * Process incoming raw message
   */
  async processMessage(rawMessage: string, traceId?: string): Promise<string | null> {
    // Parse message
    const parseResult = this.protocol.parseMessage(rawMessage);
    if (!parseResult.success) {
      const errorResponse = this.protocol.createErrorResponse(
        null,
        parseResult.error.code,
        parseResult.error.message,
        parseResult.error.data
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    const data = parseResult.data as any;

    // Check if this is a response (has result or error field, not method field)
    if ((data.result !== undefined || data.error) && data.id && !data.method) {
      // This is a response from an agent to a tool invocation request
      if (this.responseHandler) {
        this.responseHandler(data.id, data);
      }
      return null; // Don't send a response for responses
    }

    // Check if notification (no id field, no response needed)
    if (!data.id && this.protocol.validateNotification(data)) {
      await this.handleNotification(data.method, data.params);
      return null; // No response for notifications
    }

    // Validate request structure (has id field)
    const validationResult = this.protocol.validateRequest(parseResult.data);
    if (!validationResult.valid) {
      const errorResponse = this.protocol.createErrorResponse(
        null,
        validationResult.error.code,
        validationResult.error.message,
        validationResult.error.data
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    const request = validationResult.request;

    // Handle request and generate response
    return await this.handleRequest(request);
  }

  /**
   * Handle JSON-RPC request
   */
  private async handleRequest(request: JSONRPCRequest): Promise<string> {
    const handler = this.handlers.get(request.method);

    if (!handler) {
      const errorResponse = this.protocol.createErrorResponse(
        request.id,
        ErrorCodes.METHOD_NOT_FOUND,
        `Method not found: ${request.method}`
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    try {
      const result = await handler(request.method, request.params);
      const response = this.protocol.createResponse(request.id, result);
      return this.protocol.stringifyResponse(response);
    } catch (error) {
      const errorResponse = this.protocol.createErrorResponse(
        request.id,
        ErrorCodes.INTERNAL_ERROR,
        'Internal error',
        error instanceof Error ? error.message : 'Unknown error'
      );
      return this.protocol.stringifyResponse(errorResponse);
    }
  }

  /**
   * Handle notification (no response)
   */
  private async handleNotification(method: string, params: unknown): Promise<void> {
    const handler = this.handlers.get(method);
    if (handler) {
      try {
        await handler(method, params);
      } catch (error) {
        // Log error but don't respond (notifications don't expect responses)
        console.error(`Error handling notification ${method}:`, error);
      }
    }
  }

  /**
   * Get registered methods
   */
  getRegisteredMethods(): string[] {
    return Array.from(this.handlers.keys());
  }
}
