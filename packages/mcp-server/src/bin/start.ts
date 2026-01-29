#!/usr/bin/env node

/**
 * MCP Server CLI Entry Point
 * Starts the server with configuration from environment variables
 */

import { MCPServer } from '../index.js';
import { Logger } from '../logging/logger.js';

const port = parseInt(process.env.PORT || '3000', 10);
const jwtSecret = process.env.MCP_JWT_SECRET;
const logLevel = (process.env.LOG_LEVEL || 'info') as 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

// Set global log level
Logger.setGlobalLevel = logLevel;

const server = new MCPServer({
  port,
  auth: jwtSecret ? { jwtSecret } : undefined,
});

process.on('SIGINT', async () => {
  console.log('\nShutting down...');
  await server.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\nShutting down...');
  await server.stop();
  process.exit(0);
});

server.start().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
