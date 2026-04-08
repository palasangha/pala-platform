/**
 * Tests for JSON-RPC 2.0 Protocol Implementation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { JSONRPCProtocol, ErrorCodes } from '../../src/protocol/jsonrpc';

describe('JSONRPCProtocol', () => {
  let protocol: JSONRPCProtocol;

  beforeEach(() => {
    protocol = new JSONRPCProtocol();
  });

  describe('validateRequest', () => {
    it('should validate valid request', () => {
      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: 'test.method',
        params: { foo: 'bar' },
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
      if (result.valid) {
        expect(result.request.method).toBe('test.method');
        expect(result.request.id).toBe(1);
      }
    });

    it('should accept string id', () => {
      const request = {
        jsonrpc: '2.0',
        id: 'abc-123',
        method: 'test.method',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
    });

    it('should reject missing jsonrpc field', () => {
      const request = {
        id: 1,
        method: 'test.method',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(false);
      if (!result.valid) {
        expect(result.error.code).toBe(ErrorCodes.INVALID_REQUEST);
      }
    });

    it('should reject wrong jsonrpc version', () => {
      const request = {
        jsonrpc: '1.0',
        id: 1,
        method: 'test.method',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(false);
    });

    it('should reject missing method', () => {
      const request = {
        jsonrpc: '2.0',
        id: 1,
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(false);
    });

    it('should reject missing id', () => {
      const request = {
        jsonrpc: '2.0',
        method: 'test.method',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(false);
    });

    it('should allow optional params', () => {
      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: 'test.method',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
    });
  });

  describe('validateNotification', () => {
    it('should validate notification without id', () => {
      const notification = {
        jsonrpc: '2.0',
        method: 'notify.event',
        params: { data: 'test' },
      };

      expect(protocol.validateNotification(notification)).toBe(true);
    });

    it('should reject notification with wrong version', () => {
      const notification = {
        jsonrpc: '1.0',
        method: 'notify.event',
      };

      expect(protocol.validateNotification(notification)).toBe(false);
    });
  });

  describe('createResponse', () => {
    it('should create success response', () => {
      const response = protocol.createResponse(1, { success: true, data: 'result' });

      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(1);
      expect(response.result).toEqual({ success: true, data: 'result' });
      expect(response.error).toBeUndefined();
    });

    it('should handle string id', () => {
      const response = protocol.createResponse('req-123', { data: 'test' });

      expect(response.id).toBe('req-123');
    });
  });

  describe('createErrorResponse', () => {
    it('should create error response', () => {
      const response = protocol.createErrorResponse(1, ErrorCodes.INTERNAL_ERROR, 'Something went wrong', { detail: 'error details' });

      expect(response.jsonrpc).toBe('2.0');
      expect(response.id).toBe(1);
      expect(response.result).toBeUndefined();
      expect(response.error).toBeDefined();
      expect(response.error?.code).toBe(ErrorCodes.INTERNAL_ERROR);
      expect(response.error?.message).toBe('Something went wrong');
      expect(response.error?.data).toEqual({ detail: 'error details' });
    });

    it('should handle null id for parse errors', () => {
      const response = protocol.createErrorResponse(null, ErrorCodes.PARSE_ERROR, 'Parse error');

      expect(response.id).toBe('error');
    });

    it('should allow error without data', () => {
      const response = protocol.createErrorResponse(1, ErrorCodes.METHOD_NOT_FOUND, 'Method not found');

      expect(response.error?.data).toBeUndefined();
    });
  });

  describe('parseMessage', () => {
    it('should parse valid JSON', () => {
      const message = '{"jsonrpc":"2.0","id":1,"method":"test"}';
      const result = protocol.parseMessage(message);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({ jsonrpc: '2.0', id: 1, method: 'test' });
      }
    });

    it('should reject invalid JSON', () => {
      const message = '{invalid json}';
      const result = protocol.parseMessage(message);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.code).toBe(ErrorCodes.PARSE_ERROR);
      }
    });

    it('should handle empty string', () => {
      const message = '';
      const result = protocol.parseMessage(message);

      expect(result.success).toBe(false);
    });
  });

  describe('stringifyResponse', () => {
    it('should stringify response', () => {
      const response = protocol.createResponse(1, { data: 'test' });
      const stringified = protocol.stringifyResponse(response);

      expect(typeof stringified).toBe('string');
      expect(JSON.parse(stringified)).toEqual(response);
    });

    it('should stringify error response', () => {
      const response = protocol.createErrorResponse(1, ErrorCodes.INTERNAL_ERROR, 'Error message');
      const stringified = protocol.stringifyResponse(response);

      expect(typeof stringified).toBe('string');
      const parsed = JSON.parse(stringified);
      expect(parsed.error).toBeDefined();
    });
  });

  describe('MCP Protocol Compliance', () => {
    it('should handle initialize method', () => {
      const request = {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'test-client', version: '1.0.0' },
        },
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
    });

    it('should handle tools/list method', () => {
      const request = {
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/list',
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
    });

    it('should handle tools/call method', () => {
      const request = {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: {
          name: 'extract_metadata',
          arguments: { contentId: '123' },
        },
      };

      const result = protocol.validateRequest(request);
      expect(result.valid).toBe(true);
    });
  });
});
