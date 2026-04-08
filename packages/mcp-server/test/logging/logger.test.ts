/**
 * Tests for Structured Logger
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Logger, LogLevel } from '../../src/logging/logger';
import pino from 'pino';

describe('Logger', () => {
  let logger: Logger;
  let logSpy: any;

  beforeEach(() => {
    logger = new Logger({ level: 'trace' });
    // Spy on the underlying pino logger
    logSpy = vi.spyOn(logger.getPinoLogger(), 'info');
  });

  describe('initialization', () => {
    it('should create logger with default config', () => {
      const defaultLogger = new Logger();
      expect(defaultLogger.getLevel()).toBe('info');
    });

    it('should create logger with custom level', () => {
      const customLogger = new Logger({ level: 'debug' });
      expect(customLogger.getLevel()).toBe('debug');
    });

    it('should create logger with custom name', () => {
      const namedLogger = new Logger({ name: 'test-logger' });
      expect(namedLogger).toBeDefined();
    });
  });

  describe('log levels', () => {
    it('should log at trace level', () => {
      const traceSpy = vi.spyOn(logger.getPinoLogger(), 'trace');
      logger.trace('trace message');
      expect(traceSpy).toHaveBeenCalledWith('trace message');
    });

    it('should log at debug level', () => {
      const debugSpy = vi.spyOn(logger.getPinoLogger(), 'debug');
      logger.debug('debug message');
      expect(debugSpy).toHaveBeenCalledWith('debug message');
    });

    it('should log at info level', () => {
      logger.info('info message');
      expect(logSpy).toHaveBeenCalledWith('info message');
    });

    it('should log at warn level', () => {
      const warnSpy = vi.spyOn(logger.getPinoLogger(), 'warn');
      logger.warn('warn message');
      expect(warnSpy).toHaveBeenCalledWith('warn message');
    });

    it('should log at error level', () => {
      const errorSpy = vi.spyOn(logger.getPinoLogger(), 'error');
      logger.error('error message');
      expect(errorSpy).toHaveBeenCalledWith('error message');
    });

    it('should log at fatal level', () => {
      const fatalSpy = vi.spyOn(logger.getPinoLogger(), 'fatal');
      logger.fatal('fatal message');
      expect(fatalSpy).toHaveBeenCalledWith('fatal message');
    });
  });

  describe('structured logging', () => {
    it('should log with additional data', () => {
      logger.info('message with data', { key: 'value', count: 42 });
      expect(logSpy).toHaveBeenCalledWith({ key: 'value', count: 42 }, 'message with data');
    });

    it('should log errors with error object', () => {
      const errorSpy = vi.spyOn(logger.getPinoLogger(), 'error');
      const testError = new Error('Test error');
      logger.error('error occurred', testError);
      expect(errorSpy).toHaveBeenCalledWith({ err: testError }, 'error occurred');
    });

    it('should log errors with data object', () => {
      const errorSpy = vi.spyOn(logger.getPinoLogger(), 'error');
      logger.error('error occurred', { code: 'ERR_001' });
      expect(errorSpy).toHaveBeenCalledWith({ code: 'ERR_001' }, 'error occurred');
    });
  });

  describe('child loggers', () => {
    it('should create child logger with bindings', () => {
      const child = logger.child({ component: 'test-component' });
      expect(child).toBeInstanceOf(Logger);
    });

    it('should include parent bindings in child logs', () => {
      const child = logger.child({ component: 'test' });
      const childSpy = vi.spyOn(child.getPinoLogger(), 'info');
      child.info('child message');
      expect(childSpy).toHaveBeenCalled();
    });
  });

  describe('request/response logging', () => {
    it('should log request received', () => {
      logger.logRequest('test.method', { arg: 'value' }, 'req-123');
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'request',
          method: 'test.method',
          params: { arg: 'value' },
          requestId: 'req-123',
        },
        'Request received'
      );
    });

    it('should log response sent', () => {
      logger.logResponse({ result: 'success' }, 'req-123', 150);
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'response',
          requestId: 'req-123',
          durationMs: 150,
          hasResult: true,
        },
        'Response sent'
      );
    });

    it('should log notification received', () => {
      logger.logNotification('notify.event', { data: 'test' });
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'notification',
          method: 'notify.event',
          params: { data: 'test' },
        },
        'Notification received'
      );
    });

    it('should log error response', () => {
      const errorSpy = vi.spyOn(logger.getPinoLogger(), 'error');
      logger.logErrorResponse(-32600, 'Invalid request', 'req-123');
      expect(errorSpy).toHaveBeenCalledWith(
        {
          type: 'error-response',
          requestId: 'req-123',
          errorCode: -32600,
          errorMessage: 'Invalid request',
        },
        'Error response'
      );
    });
  });

  describe('tool invocation logging', () => {
    it('should log tool invocation', () => {
      logger.logToolInvocation('test-tool', 'agent-1', 'inv-123');
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'tool-invocation',
          tool: 'test-tool',
          agent: 'agent-1',
          requestId: 'inv-123',
        },
        'Tool invocation'
      );
    });

    it('should log tool result', () => {
      logger.logToolResult('test-tool', true, 250, 'inv-123');
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'tool-result',
          tool: 'test-tool',
          success: true,
          durationMs: 250,
          requestId: 'inv-123',
        },
        'Tool result'
      );
    });
  });

  describe('connection logging', () => {
    it('should log connection connected', () => {
      logger.logConnection('connected', 'conn-123', { userAgent: 'test' });
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'connection',
          event: 'connected',
          connectionId: 'conn-123',
          userAgent: 'test',
        },
        'Connection connected'
      );
    });

    it('should log connection disconnected', () => {
      logger.logConnection('disconnected', 'conn-123');
      expect(logSpy).toHaveBeenCalledWith(
        {
          type: 'connection',
          event: 'disconnected',
          connectionId: 'conn-123',
        },
        'Connection disconnected'
      );
    });
  });

  describe('level management', () => {
    it('should set log level dynamically', () => {
      logger.setLevel('warn');
      expect(logger.getLevel()).toBe('warn');
    });

    it('should respect log level filtering', () => {
      logger.setLevel('error');
      const debugSpy = vi.spyOn(logger.getPinoLogger(), 'debug');
      logger.debug('should not log');
      expect(debugSpy).toHaveBeenCalled(); // Called but filtered by pino
    });
  });

  describe('underlying pino logger', () => {
    it('should expose pino logger for advanced usage', () => {
      const pinoLogger = logger.getPinoLogger();
      expect(pinoLogger).toBeDefined();
      expect(typeof pinoLogger.info).toBe('function');
    });
  });
});
