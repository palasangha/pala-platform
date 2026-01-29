/**
 * Protocol Handler
 * Coordinates message handling, method routing, and response generation
 */

import { JSONRPCProtocol, ErrorCodes } from './jsonrpc';
import type { JSONRPCRequest, JSONRPCResponse } from '../types';
import { Logger } from '../logging/logger';

const logger = new Logger({ name: 'ProtocolHandler', level: (process.env.LOG_LEVEL as any) || 'info' });

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
    logger.debug('🔍 TRACE: ProtocolHandler.processMessage() called', { 
      messageLength: rawMessage.length,
      messagePreview: rawMessage.substring(0, 100),
      traceId 
    });

    // Parse message
    const parseResult = this.protocol.parseMessage(rawMessage);
    if (!parseResult.success) {
      logger.error('❌ TRACE: Message parse failed', { error: parseResult.error });
      const errorResponse = this.protocol.createErrorResponse(
        null,
        parseResult.error.code,
        parseResult.error.message,
        parseResult.error.data
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    const data = parseResult.data as any;
    logger.debug('✓ TRACE: Message parsed', { 
      hasMethod: !!data.method,
      method: data.method,
      hasId: !!data.id,
      id: data.id,
      hasResult: data.result !== undefined,
      hasError: !!data.error
    });

    // Check if this is a response (has result or error field, not method field)
    if ((data.result !== undefined || data.error) && data.id && !data.method) {
      // This is a response from an agent to a tool invocation request
      logger.info('🔍 TRACE: Message is a response from agent', { id: data.id });
      if (this.responseHandler) {
        logger.debug('✓ TRACE: Forwarding to response handler', { id: data.id });
        this.responseHandler(data.id, data);
      } else {
        logger.warn('⚠️ TRACE: No response handler registered');
      }
      return null; // Don't send a response for responses
    }

    // Check if notification (no id field, no response needed)
    if (!data.id && this.protocol.validateNotification(data)) {
      logger.debug('🔍 TRACE: Message is a notification', { method: data.method });
      await this.handleNotification(data.method, data.params);
      return null; // No response for notifications
    }

    // Validate request structure (has id field)
    const validationResult = this.protocol.validateRequest(parseResult.data);
    if (!validationResult.valid) {
      logger.error('❌ TRACE: Request validation failed', { error: validationResult.error });
      const errorResponse = this.protocol.createErrorResponse(
        null,
        validationResult.error.code,
        validationResult.error.message,
        validationResult.error.data
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    const request = validationResult.request;
    logger.info('✓ TRACE: Request validated, handling', { method: request.method, id: request.id });

    // Handle request and generate response
    return await this.handleRequest(request);
  }

  /**
   * Handle JSON-RPC request
   */
  private async handleRequest(request: JSONRPCRequest): Promise<string> {
    logger.info('🔍 TRACE: handleRequest() called', { method: request.method, id: request.id });

    const handler = this.handlers.get(request.method);

    if (!handler) {
      logger.error('❌ TRACE: No handler registered for method', { method: request.method });
      const errorResponse = this.protocol.createErrorResponse(
        request.id,
        ErrorCodes.METHOD_NOT_FOUND,
        `Method not found: ${request.method}`
      );
      return this.protocol.stringifyResponse(errorResponse);
    }

    logger.debug('✓ TRACE: Handler found, executing', { method: request.method });

    try {
      const result = await handler(request.method, request.params);
      logger.info('✓ TRACE: Handler executed successfully', { method: request.method, hasResult: !!result });
      const response = this.protocol.createResponse(request.id, result);
      return this.protocol.stringifyResponse(response);
    } catch (error) {
      logger.error('❌ TRACE: Handler threw error', { 
        method: request.method, 
        error: error instanceof Error ? error.message : String(error)
      });
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
