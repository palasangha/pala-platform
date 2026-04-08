/**
 * Structured Logger using Pino
 * 
 * Provides JSON-structured logging with:
 * - Multiple log levels (trace, debug, info, warn, error, fatal)
 * - Request/response logging
 * - Child loggers for components
 * - Performance timing
 */

import pino, { Logger as PinoLogger, LoggerOptions } from 'pino';

/**
 * Log levels
 */
export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

/**
 * Logger configuration
 */
export interface LoggerConfig {
  level?: LogLevel;
  pretty?: boolean;
  name?: string;
  redact?: string[];
}

/**
 * Structured logger wrapper
 */
export class Logger {
  private logger: PinoLogger;

  constructor(config: LoggerConfig = {}) {
    const options: LoggerOptions = {
      level: config.level || 'info',
      name: config.name || 'mcp-server',
      redact: config.redact || ['password', 'token', 'authorization'],
    };

    // Pretty printing for development
    if (config.pretty) {
      this.logger = pino({
        ...options,
        transport: {
          target: 'pino-pretty',
          options: {
            colorize: true,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname',
          },
        },
      });
    } else {
      this.logger = pino(options);
    }
  }

  /**
   * Create child logger with additional context
   */
  child(bindings: Record<string, any>): Logger {
    const childLogger = new Logger();
    childLogger.logger = this.logger.child(bindings);
    return childLogger;
  }

  /**
   * Log at trace level
   */
  trace(message: string, data?: Record<string, any>): void {
    if (data) {
      this.logger.trace(data, message);
    } else {
      this.logger.trace(message);
    }
  }

  /**
   * Log at debug level
   */
  debug(message: string, data?: Record<string, any>): void {
    if (data) {
      this.logger.debug(data, message);
    } else {
      this.logger.debug(message);
    }
  }

  /**
   * Log at info level
   */
  info(message: string, data?: Record<string, any>): void {
    if (data) {
      this.logger.info(data, message);
    } else {
      this.logger.info(message);
    }
  }

  /**
   * Log at warn level
   */
  warn(message: string, data?: Record<string, any>): void {
    if (data) {
      this.logger.warn(data, message);
    } else {
      this.logger.warn(message);
    }
  }

  /**
   * Log at error level
   */
  error(message: string, error?: Error | Record<string, any>): void {
    if (error instanceof Error) {
      this.logger.error({ err: error }, message);
    } else if (error) {
      this.logger.error(error, message);
    } else {
      this.logger.error(message);
    }
  }

  /**
   * Log at fatal level
   */
  fatal(message: string, error?: Error | Record<string, any>): void {
    if (error instanceof Error) {
      this.logger.fatal({ err: error }, message);
    } else if (error) {
      this.logger.fatal(error, message);
    } else {
      this.logger.fatal(message);
    }
  }

  /**
   * Log request received
   */
  logRequest(method: string, params?: any, id?: string | number): void {
    this.info('Request received', {
      type: 'request',
      method,
      params,
      requestId: id,
    });
  }

  /**
   * Log response sent
   */
  logResponse(result?: any, id?: string | number, durationMs?: number): void {
    this.info('Response sent', {
      type: 'response',
      requestId: id,
      durationMs,
      hasResult: result !== undefined,
    });
  }

  /**
   * Log notification received
   */
  logNotification(method: string, params?: any): void {
    this.info('Notification received', {
      type: 'notification',
      method,
      params,
    });
  }

  /**
   * Log error response
   */
  logErrorResponse(code: number, message: string, id?: string | number): void {
    this.error('Error response', {
      type: 'error-response',
      requestId: id,
      errorCode: code,
      errorMessage: message,
    });
  }

  /**
   * Log tool invocation
   */
  logToolInvocation(toolName: string, agentId: string, requestId?: string): void {
    this.info('Tool invocation', {
      type: 'tool-invocation',
      tool: toolName,
      agent: agentId,
      requestId,
    });
  }

  /**
   * Log tool result
   */
  logToolResult(
    toolName: string,
    success: boolean,
    durationMs?: number,
    requestId?: string
  ): void {
    this.info('Tool result', {
      type: 'tool-result',
      tool: toolName,
      success,
      durationMs,
      requestId,
    });
  }

  /**
   * Log connection event
   */
  logConnection(event: 'connected' | 'disconnected', connectionId: string, metadata?: any): void {
    this.info(`Connection ${event}`, {
      type: 'connection',
      event,
      connectionId,
      ...metadata,
    });
  }

  /**
   * Get the underlying Pino logger (for advanced usage)
   */
  getPinoLogger(): PinoLogger {
    return this.logger;
  }

  /**
   * Set log level dynamically
   */
  setLevel(level: LogLevel): void {
    this.logger.level = level;
  }

  /**
   * Get current log level
   */
  getLevel(): string {
    return this.logger.level;
  }
}

/**
 * Default logger instance
 */
export const defaultLogger = new Logger();
