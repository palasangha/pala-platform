/**
 * Supervisor service API client
 *
 * Provides methods for interacting with the supervisor API endpoints
 * for managing remote worker deployments.
 */
import api from './api';
import type {
  DeploymentsResponse,
  DeploymentResponse,
  DeploymentFormData,
  OperationResponse,
  HealthResponse,
  StatsResponse,
  LogsResponse,
  SSHKeysResponse,
  ConnectionTestResponse
} from '@/types/supervisor';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const supervisorAPI = {
  /**
   * Get all deployments for current user
   */
  getDeployments: async (): Promise<DeploymentsResponse> => {
    const { data } = await api.get('/supervisor/deployments');
    return data;
  },

  /**
   * Get specific deployment by ID
   */
  getDeployment: async (deploymentId: string): Promise<DeploymentResponse> => {
    const { data } = await api.get(`/supervisor/deployments/${deploymentId}`);
    return data;
  },

  /**
   * Create new worker deployment
   */
  createDeployment: async (deploymentConfig: DeploymentFormData): Promise<DeploymentResponse> => {
    const { data } = await api.post('/supervisor/deployments', deploymentConfig);
    return data;
  },

  /**
   * Start workers on deployment
   */
  startWorkers: async (deploymentId: string): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/start`);
    return data;
  },

  /**
   * Stop workers on deployment
   */
  stopWorkers: async (deploymentId: string): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/stop`);
    return data;
  },

  /**
   * Restart workers on deployment
   */
  restartWorkers: async (deploymentId: string): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/restart`);
    return data;
  },

  /**
   * Update Docker image on deployment workers
   */
  updateDockerImage: async (deploymentId: string): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/update-image`);
    return data;
  },

  /**
   * Scale worker count
   */
  scaleWorkers: async (deploymentId: string, workerCount: number): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/scale`, {
      worker_count: workerCount
    });
    return data;
  },

  /**
   * Delete deployment
   */
  deleteDeployment: async (deploymentId: string): Promise<OperationResponse> => {
    const { data } = await api.delete(`/supervisor/deployments/${deploymentId}`);
    return data;
  },

  /**
   * Get health status of deployment
   */
  getHealth: async (deploymentId: string): Promise<HealthResponse> => {
    const { data } = await api.get(`/supervisor/deployments/${deploymentId}/health`);
    return data;
  },

  /**
   * Get detailed statistics for deployment
   */
  getStats: async (deploymentId: string): Promise<StatsResponse> => {
    const { data } = await api.get(`/supervisor/deployments/${deploymentId}/stats`);
    return data;
  },

  /**
   * Get container logs
   */
  getLogs: async (deploymentId: string, containerName: string, lines = 100): Promise<LogsResponse> => {
    const { data } = await api.get(`/supervisor/deployments/${deploymentId}/logs`, {
      params: { container_name: containerName, lines }
    });
    return data;
  },

  /**
   * Stream container logs via Server-Sent Events
   *
   * @param deploymentId - Deployment ID
   * @param containerName - Container name (empty string or omit for all docker-compose logs)
   * @param onLog - Callback for each log line
   * @param onError - Callback for errors
   * @returns EventSource instance (can be closed with .close())
   */
  streamLogs: (
    deploymentId: string,
    containerName: string = '',
    onLog: (log: string) => void,
    onError?: (error: string) => void
  ): EventSource => {
    const token = localStorage.getItem('access_token');

    if (!token) {
      const errorMsg = 'No authentication token found. Please log in again.';
      if (onError) {
        onError(errorMsg);
      }
      throw new Error(errorMsg);
    }

    // Note: EventSource doesn't support custom headers in standard implementation
    // We'll include the token in the URL as a query parameter
    // If containerName is empty, don't include it in the URL (will get all docker-compose logs)
    const containerParam = containerName ? `&container_name=${encodeURIComponent(containerName)}` : '';
    const url = `${API_BASE_URL}/supervisor/deployments/${deploymentId}/logs/stream?token=${token}${containerParam}`;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          if (onError) {
            onError(data.error);
          }
        } else if (data.log) {
          onLog(data.log);
        } else if (data.status === 'connected') {
          console.log('Connected to log stream:', data.container);
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      
      // Try to get more details from the event
      if (error instanceof Event) {
        const readyState = eventSource.readyState;
        let errorMsg = 'Connection to log stream failed';
        
        if (readyState === EventSource.CLOSED) {
          errorMsg = 'Log stream connection closed';
        } else if (readyState === EventSource.CONNECTING) {
          errorMsg = 'Failed to connect to log stream (connection timeout or server error)';
        }
        
        if (onError) {
          onError(errorMsg);
        }
      }
      
      // Close the connection to prevent reconnection attempts
      eventSource.close();
    };

    return eventSource;
  },

  /**
   * Get NSQ queue statistics
   */
  getNSQStats: async () => {
    const { data } = await api.get('/supervisor/nsq/stats');
    return data;
  },

  /**
   * List available SSH keys
   */
  getSSHKeys: async (): Promise<SSHKeysResponse> => {
    const { data } = await api.get('/supervisor/ssh-keys');
    return data;
  },

  /**
   * Test SSH connection before deployment
   */
  testConnection: async (
    host: string,
    port: number,
    username: string,
    sshKeyName: string
  ): Promise<ConnectionTestResponse> => {
    const { data } = await api.post('/supervisor/test-connection', {
      host,
      port,
      username,
      ssh_key_name: sshKeyName
    });
    return data;
  },

  /**
   * Get default configuration values for worker deployment
   */
  getDefaultConfig: async () => {
    const { data } = await api.get('/supervisor/config/defaults');
    return data;
  },

  /**
   * Build and push worker image to registry
   * Streams progress updates via callback
   */
  buildAndPushWorker: async (onProgress: (progress: number, status: string, log?: string) => void): Promise<OperationResponse> => {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
      throw new Error('No authentication token found. Please log in again.');
    }

    const url = `${API_BASE_URL}/supervisor/build-push-worker?token=${token}`;
    const eventSource = new EventSource(url);
    
    return new Promise((resolve, reject) => {
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.error) {
            reject({ success: false, error: data.error });
            eventSource.close();
          } else if (data.log) {
            onProgress(0, '', data.log);
          } else if (data.progress !== undefined) {
            onProgress(data.progress, data.status || '');
          } else if (data.success) {
            resolve({ success: true });
            eventSource.close();
          }
        } catch (error) {
          console.error('Error parsing build progress:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('Build stream error:', error);
        reject({ success: false, error: 'Connection to build stream failed' });
        eventSource.close();
      };
    });
  },

  /**
   * Scale the number of worker containers in a deployment
   */
  scaleDeployment: async (deploymentId: string, workerCount: number): Promise<OperationResponse> => {
    const { data } = await api.post(`/supervisor/deployments/${deploymentId}/scale`, {
      worker_count: workerCount
    });
    return data;
  }
};

export default supervisorAPI;
