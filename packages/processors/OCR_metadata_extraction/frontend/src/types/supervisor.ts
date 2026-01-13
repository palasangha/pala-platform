/**
 * TypeScript type definitions for Supervisor service
 */

export interface ContainerInfo {
  container_id: string;
  container_name: string;
  status: string;
  started_at: string;
  health: 'healthy' | 'unhealthy' | 'unknown';
}

export interface ProviderConfig {
  google_vision_enabled: boolean;
  tesseract_enabled: boolean;
  ollama_enabled: boolean;
  vllm_enabled: boolean;
  easyocr_enabled: boolean;
  azure_enabled: boolean;
}

export interface Deployment {
  id: string;
  user_id: string;
  worker_id: string;

  // Connection config
  host: string;
  port: number;
  username: string;
  ssh_key_name: string;

  // Worker config
  worker_name: string;
  worker_count: number;
  nsqd_address: string;
  nsqlookupd_addresses: string[];
  mongo_uri: string;
  server_url: string;
  providers: ProviderConfig;

  // Status
  status: 'deploying' | 'running' | 'stopped' | 'error' | 'unreachable';
  containers: ContainerInfo[];
  health_status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  error_message?: string;

  // Timestamps
  created_at: string;
  updated_at: string;
  deployed_at?: string;
  last_health_check?: string;
  last_accessed?: string;
}

export interface DeploymentFormData {
  worker_name: string;
  host: string;
  port: number;
  username: string;
  ssh_key_name: string;
  worker_count: number;
  nsqd_address: string;
  nsqlookupd_addresses: string[];
  mongo_uri: string;
  server_url: string;
  providers: ProviderConfig;
}

export interface HealthData {
  health_status: 'healthy' | 'degraded' | 'unhealthy' | 'unreachable';
  containers: ContainerInfo[];
  running_containers: number;
  total_containers: number;
  cpu_usage: number;
  memory_usage: number;
  ssh_connected: boolean;
  error_message?: string;
}

export interface WorkerStats {
  health: HealthData;
  deployment_info: {
    host: string;
    worker_count: number;
    worker_name: string;
  };
}

export interface DeploymentsResponse {
  success: boolean;
  deployments: Deployment[];
  count: number;
  error?: string;
}

export interface DeploymentResponse {
  success: boolean;
  deployment: Deployment;
  message?: string;
  error?: string;
}

export interface OperationResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface HealthResponse {
  success: boolean;
  health: HealthData;
  error?: string;
}

export interface StatsResponse {
  success: boolean;
  stats: WorkerStats;
  error?: string;
}

export interface LogsResponse {
  success: boolean;
  logs: string;
  container_name: string;
  error?: string;
}

export interface SSHKeysResponse {
  success: boolean;
  ssh_keys: string[];
  error?: string;
}

export interface ConnectionTestResponse {
  success: boolean;
  message?: string;
  output?: string;
}
