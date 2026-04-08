/**
 * Basic server initialization tests
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { MCPServer } from '../src/server';

describe('MCPServer', () => {
  let server: MCPServer;

  beforeEach(() => {
    server = new MCPServer({
      port: 3000,
      logging: { level: 'error' },
    });
  });

  afterEach(async () => {
    await server.stop();
  });

  it('should create server instance', () => {
    expect(server).toBeInstanceOf(MCPServer);
  });

  it('should start and stop cleanly', async () => {
    await server.start();
    await server.stop();
  });
});
