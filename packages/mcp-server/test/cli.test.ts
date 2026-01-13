/**
 * CLI Entry Point Test
 * Validates that start.ts can be executed and server starts correctly
 */

import { describe, it, expect } from 'vitest';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const CLI_PATH = resolve(__dirname, '../src/bin/start.ts');
const TEST_PORT = 10001;

describe('CLI Entry Point', () => {
  it('should start server successfully via CLI', async () => {
    return new Promise<void>((resolveTest, reject) => {
      const proc = spawn('tsx', [CLI_PATH], {
        env: { ...process.env, PORT: TEST_PORT.toString() },
        stdio: 'pipe',
      });

      let output = '';
      let hasStarted = false;

      proc.stdout?.on('data', (data) => {
        output += data.toString();
        if (output.includes('MCP Server started successfully')) {
          hasStarted = true;
          proc.kill('SIGTERM');
        }
      });

      proc.stderr?.on('data', (data) => {
        output += data.toString();
      });

      proc.on('close', (code) => {
        if (hasStarted) {
          expect(output).toContain('Starting MCP Server');
          expect(output).toContain('MCP Server started successfully');
          expect(output).toContain('Stopping MCP Server');
          resolveTest();
        } else {
          reject(new Error(`Server failed to start. Output: ${output}`));
        }
      });

      proc.on('error', (err) => {
        reject(err);
      });

      // Timeout after 5 seconds
      setTimeout(() => {
        if (!hasStarted) {
          proc.kill('SIGTERM');
          reject(new Error(`Test timeout. Output: ${output}`));
        }
      }, 5000);
    });
  }, 10000);
});
