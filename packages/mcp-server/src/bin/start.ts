#!/usr/bin/env node

/**
 * MCP Server CLI Entry Point
 * Starts the server with configuration from environment variables
 */

import { MCPServer } from '../src/index.js';

const port = parseInt(process.env.PORT || '3000', 10);
const authSecret = process.env.MCP_AUTH_SECRET;

const server = new MCPServer({
  port,
  authSecret,
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
