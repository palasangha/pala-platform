/**
 * Storage Tool for MCP Server
 * Provides storage capabilities as an MCP tool following the agent provider pattern
 */

import { spawn } from 'child_process';
import { join } from 'path';
import crypto from 'crypto';

export const STORAGE_AGENT_ID = 'pala-storage-provider';

export interface StorageResult {
  content_id: string;
  file_hash: string;
  backend: string;
  version: number;
  deduplication: boolean;
  message: string;
}

export interface StorageToolDefinition {
  name: string;
  description: string;
  agentId: string;
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required: string[];
    additionalProperties?: boolean;
  };
}

export class StorageTool {
  private pythonPath: string;
  private scriptPath: string;

  constructor() {
    // Path to Python storage script
    this.pythonPath = '/opt/homebrew/bin/python3';
    this.scriptPath = join(
      process.cwd(),
      '..',
      '..',
      'packages',
      'storage',
      'api',
      'storage_cli.py'
    );
  }

  /**
   * Store content with backend selection
   */
  async storeContent(params: {
    content: string;
    content_type: string;
    backend?: string;  // Optional: specific backend to use
    metadata?: Record<string, any>;
  }): Promise<StorageResult> {
    const { content, content_type, backend, metadata = {} } = params;

    return new Promise((resolve, reject) => {
      const args = [
        this.scriptPath,
        'store',
        '--content-type',
        content_type,
        '--metadata',
        JSON.stringify(metadata),
      ];

      // Add backend if specified
      if (backend) {
        args.push('--backend');
        args.push(backend);
      }

      const python = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      // Send content via stdin
      python.stdin.write(content);
      python.stdin.end();

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Storage failed: ${stderr}`));
          return;
        }

        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (err) {
          reject(new Error(`Failed to parse storage result: ${stdout}`));
        }
      });
    });
  }

  /**
   * Retrieve content by ID
   */
  async retrieveContent(contentId: string): Promise<{
    content: string;
    metadata: Record<string, any>;
  }> {
    return new Promise((resolve, reject) => {
      const args = [this.scriptPath, 'retrieve', contentId];

      const python = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Retrieval failed: ${stderr}`));
          return;
        }

        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (err) {
          reject(new Error(`Failed to parse retrieval result: ${stdout}`));
        }
      });
    });
  }

  /**
   * List all stored content
   */
  async listContent(): Promise<any[]> {
    return new Promise((resolve, reject) => {
      const args = [this.scriptPath, 'list'];

      const python = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`List failed: ${stderr}`));
          return;
        }

        try {
          const result = JSON.parse(stdout);
          resolve(result.items || []);
        } catch (err) {
          reject(new Error(`Failed to parse list result: ${stdout}`));
        }
      });
    });
  }

  /**
   * List available storage backends
   */
  async listBackends(): Promise<any> {
    return new Promise((resolve, reject) => {
      const args = [this.scriptPath, 'backends'];

      const python = spawn(this.pythonPath, args);
      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Backends list failed: ${stderr}`));
          return;
        }

        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (err) {
          reject(new Error(`Failed to parse backends result: ${stdout}`));
        }
      });
    });
  }
}

/**
 * Get storage provider tools definition
 * Returns tool definitions that should be registered as from the storage provider
 */
export function getStorageTools(): StorageToolDefinition[] {
  return [
    {
      name: 'store-content',
      description: 'Store content with automatic deduplication via SHA-256',
      agentId: STORAGE_AGENT_ID,
      inputSchema: {
        type: 'object',
        properties: {
          content: {
            type: 'string',
            description: 'Content to store',
          },
          content_type: {
            type: 'string',
            description: 'Type of content (document, audio, video, etc.)',
          },
          metadata: {
            type: 'object',
            description: 'Additional metadata',
          },
        },
        required: ['content', 'content_type'],
        additionalProperties: true,
      },
    },
    {
      name: 'retrieve-content',
      description: 'Retrieve stored content by ID',
      agentId: STORAGE_AGENT_ID,
      inputSchema: {
        type: 'object',
        properties: {
          content_id: {
            type: 'string',
            description: 'Content ID to retrieve',
          },
        },
        required: ['content_id'],
        additionalProperties: true,
      },
    },
    {
      name: 'list-content',
      description: 'List all stored content with pagination',
      agentId: STORAGE_AGENT_ID,
      inputSchema: {
        type: 'object',
        properties: {
          limit: {
            type: 'number',
            description: 'Maximum number of items to return',
          },
          offset: {
            type: 'number',
            description: 'Number of items to skip',
          },
        },
        required: [],
        additionalProperties: true,
      },
    },
    {
      name: 'list-backends',
      description: 'List available storage backends and get default backend',
      agentId: STORAGE_AGENT_ID,
      inputSchema: {
        type: 'object',
        properties: {},
        required: [],
        additionalProperties: true,
      },
    },
  ];
}
