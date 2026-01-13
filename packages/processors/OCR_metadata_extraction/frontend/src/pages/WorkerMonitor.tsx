import React, { useState, useEffect } from 'react';
import api from '@/services/api';
import networkDiagnostics from '@/services/networkDiagnostics';
import { CheckCircle, Clock, Server, AlertCircle, Activity } from 'lucide-react';

interface WorkerInfo {
  client_id: string;
  hostname: string;
  container_name?: string;
  deployment_type?: string;
  service_name?: string;
  display_name?: string;
  remote_address: string;
  state: number;
  status: string;
  activity: string;
  ready_count: number;
  in_flight_count: number;
  message_count: number;
  finish_count: number;
  requeue_count: number;
  connected_duration: number;
  user_agent: string;
  version: string;
}

interface WorkerStats {
  success: boolean;
  workers: WorkerInfo[];
  worker_count: number;
  channel_stats: {
    depth: number;
    in_flight_count: number;
    deferred_count: number;
    requeue_count: number;
    timeout_count: number;
    message_count: number;
    client_count: number;
  };
  topic_stats: {
    depth: number;
    message_count: number;
    channel_count: number;
  };
  nsq_address: string;
}

export const WorkerMonitor: React.FC = () => {
  const [workerStats, setWorkerStats] = useState<WorkerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadWorkerStats = async () => {
    try {
      console.log('[WORKERS] Loading worker stats...');
      const statsResponse = await api.get('/workers/stats').catch(err => {
        console.error('[WORKERS-STATS] Failed to fetch stats:', err.message, err.code);
        throw err;
      });
      console.log('[WORKERS] Successfully loaded data');
      setWorkerStats(statsResponse.data);
      setError('');
    } catch (err: any) {
      console.error('[WORKERS] Error:', err);
      const errorMsg = err.response?.data?.error || err.message || 'Failed to load worker statistics';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (nanoseconds: number): string => {
    const seconds = Math.floor(nanoseconds / 1_000_000_000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  useEffect(() => {
    loadWorkerStats();
  }, []);

  // Auto-refresh every 5 seconds if enabled
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadWorkerStats, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 text-green-800';
      case 'connected':
      case 'subscribing':
        return 'bg-blue-100 text-blue-800';
      case 'disconnected':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActivityColor = (activity: string): string => {
    switch (activity) {
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'idle':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const runNetworkDiagnostics = async () => {
    console.log('[WORKERS] Running network diagnostics...');
    networkDiagnostics.getEnvironmentInfo();
    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
    const fullURL = new URL(baseURL, window.location.origin).toString();
    await networkDiagnostics.runFullDiagnostics(fullURL + '/workers/stats');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
        {/* Header Controls */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Worker Monitor</h2>
            <p className="text-sm text-gray-600 mt-1">
              NSQ Server: {workerStats?.nsq_address || 'Unknown'}
            </p>
          </div>
          <div className="flex gap-4 items-center">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Auto-refresh (5s)</span>
            </label>
            <button
              onClick={loadWorkerStats}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Refresh Now
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4 border border-red-200">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Error loading data</p>
                <p className="text-sm text-red-700 mt-1">{error}</p>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={loadWorkerStats}
                    className="text-sm px-3 py-1 bg-red-100 text-red-800 rounded hover:bg-red-200 font-medium"
                  >
                    Retry
                  </button>
                  <button
                    onClick={runNetworkDiagnostics}
                    className="text-sm px-3 py-1 bg-red-100 text-red-800 rounded hover:bg-red-200 font-medium"
                  >
                    Diagnose
                  </button>
                </div>
                <p className="text-xs text-red-600 mt-2">Open browser console (F12) to see diagnostic logs</p>
              </div>
            </div>
          </div>
        )}

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Server className="w-8 h-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Connected Workers</p>
                <p className="text-2xl font-bold text-gray-900">{workerStats?.worker_count || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-yellow-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Queue Depth</p>
                <p className="text-2xl font-bold text-gray-900">{workerStats?.channel_stats?.depth || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Processing</p>
                <p className="text-2xl font-bold text-gray-900">{workerStats?.channel_stats?.in_flight_count || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Processed</p>
                <p className="text-2xl font-bold text-gray-900">{workerStats?.channel_stats?.message_count || 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Workers Table */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Connected Workers</h3>
          </div>

          {!workerStats?.workers || workerStats.workers.length === 0 ? (
            <div className="text-center py-12">
              <Server className="w-16 h-16 mx-auto text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">No workers connected</h3>
              <p className="mt-2 text-sm text-gray-500">
                Start workers to see them appear here
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Worker ID / Hostname
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Activity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Processing
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Completed
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Connected
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Address
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {workerStats.workers.map((worker) => (
                    <tr key={worker.client_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {worker.display_name || worker.container_name || worker.client_id}
                        </div>
                        <div className="text-sm text-gray-500">
                          {worker.deployment_type && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 mr-2">
                              {worker.deployment_type}
                            </span>
                          )}
                          {worker.hostname}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(worker.status)}`}>
                          {worker.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getActivityColor(worker.activity)}`}>
                          {worker.activity}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {worker.in_flight_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {worker.finish_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDuration(worker.connected_duration)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {worker.remote_address}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Channel Statistics */}
        {workerStats?.channel_stats && (
          <div className="mt-8 bg-white shadow rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Channel Statistics</h3>
              <p className="text-sm text-gray-500">bulk_ocr_workers channel</p>
            </div>
            <div className="p-6">
              <dl className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Messages in Queue</dt>
                  <dd className="mt-1 text-2xl font-semibold text-gray-900">{workerStats.channel_stats.depth}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">In Flight</dt>
                  <dd className="mt-1 text-2xl font-semibold text-gray-900">{workerStats.channel_stats.in_flight_count}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Requeued</dt>
                  <dd className="mt-1 text-2xl font-semibold text-gray-900">{workerStats.channel_stats.requeue_count}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Timeouts</dt>
                  <dd className="mt-1 text-2xl font-semibold text-gray-900">{workerStats.channel_stats.timeout_count}</dd>
                </div>
              </dl>
            </div>
          </div>
        )}
    </div>
  );
};

export default WorkerMonitor;
