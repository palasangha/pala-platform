import React, { useState, useEffect, useRef } from 'react';
import supervisorAPI from '@/services/supervisorService';
import type { Deployment, DeploymentFormData } from '@/types/supervisor';
import {
  Play, Square, RotateCw, Trash2, Plus, X, Eye,
  CheckCircle, XCircle, AlertTriangle, Clock, RefreshCw, Upload, Maximize2, Server, Activity
} from 'lucide-react';

export const SupervisorDashboard: React.FC = () => {

  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [logsStreaming, setLogsStreaming] = useState(false);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  // Build and push state
  const [showBuildModal, setShowBuildModal] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildStatus, setBuildStatus] = useState('');
  const [buildLogs, setBuildLogs] = useState<string[]>([]);

  // Scale state
  const [showScaleModal, setShowScaleModal] = useState(false);
  const [scaleDeploymentId, setScaleDeploymentId] = useState<string | null>(null);
  const [newWorkerCount, setNewWorkerCount] = useState(1);
  const [isScaling, setIsScaling] = useState(false);
  const [scaleMessage, setScaleMessage] = useState('');

  // Refs
  const logsEndRef = useRef<HTMLDivElement>(null);

  // SSH keys
  const [sshKeys, setSSHKeys] = useState<string[]>([]);

  // Form state
  const [formData, setFormData] = useState<DeploymentFormData>({
    worker_name: '',
    host: '',
    port: 22,
    username: '',
    ssh_key_name: '',
    worker_count: 1,
    nsqd_address: '',
    nsqlookupd_addresses: [''],
    mongo_uri: '',
    server_url: '',
    providers: {
      google_vision_enabled: true,
      tesseract_enabled: true,
      ollama_enabled: false,
      vllm_enabled: false,
      easyocr_enabled: false,
      azure_enabled: false
    }
  });

  const loadDeployments = async () => {
    try {
      const response = await supervisorAPI.getDeployments();
      if (response.success) {
        setDeployments(response.deployments);
        setError('');
      } else {
        setError(response.error || 'Failed to load deployments');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load deployments');
    } finally {
      setLoading(false);
    }
  };

  const loadSSHKeys = async () => {
    try {
      const response = await supervisorAPI.getSSHKeys();
      if (response.success) {
        setSSHKeys(response.ssh_keys);
      }
    } catch (err) {
      console.error('Failed to load SSH keys:', err);
    }
  };

  const loadDefaultConfig = async () => {
    try {
      const response = await supervisorAPI.getDefaultConfig();
      if (response.success) {
        const config = response.config;
        setFormData(prev => ({
          ...prev,
          nsqd_address: config.nsqd_address || '',
          nsqlookupd_addresses: [config.nsqlookupd_addresses || ''],
          mongo_uri: config.mongo_uri || '',
          server_url: config.server_url || ''
        }));
      }
    } catch (err) {
      console.error('Failed to load default config:', err);
    }
  };

  useEffect(() => {
    loadDeployments();
    loadSSHKeys();
    loadDefaultConfig();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadDeployments, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // Cleanup event source when logs modal closes
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleCreateDeployment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await supervisorAPI.createDeployment(formData);
      if (response.success) {
        // Show success message
        alert('Deployment started! Status will update automatically.');
        
        // Close modal and reset form
        setShowAddModal(false);
        setFormData({
          worker_name: '',
          host: '',
          port: 22,
          username: '',
          ssh_key_name: '',
          worker_count: 1,
          nsqd_address: '',
          nsqlookupd_addresses: [''],
          mongo_uri: '',
          server_url: '',
          providers: {
            google_vision_enabled: true,
            tesseract_enabled: true,
            ollama_enabled: false,
            vllm_enabled: false,
            easyocr_enabled: false,
            azure_enabled: false
          }
        });

        // Load deployments immediately to show the new 'deploying' status
        loadDeployments();

        // Start polling for deployment status (every 3 seconds, for up to 10 minutes)
        const deploymentId = response.deployment.id;
        const pollCount = { current: 0 };
        const pollInterval = setInterval(async () => {
          pollCount.current++;
          
          // Stop polling after 200 iterations (10 minutes)
          if (pollCount.current > 200) {
            clearInterval(pollInterval);
            console.log(`Stopped polling for deployment ${deploymentId}`);
            return;
          }

          try {
            const deploymentStatus = await supervisorAPI.getDeployment(deploymentId);
            if (deploymentStatus.deployment.status !== 'deploying') {
              // Deployment finished (success or error)
              clearInterval(pollInterval);
              loadDeployments();
              
              if (deploymentStatus.deployment.status === 'running') {
                alert(`✅ Deployment successful! Workers are running.`);
              } else if (deploymentStatus.deployment.status === 'error') {
                alert(`❌ Deployment failed: ${deploymentStatus.deployment.error_message}`);
              }
            }
          } catch (pollErr) {
            console.error('Error polling deployment status:', pollErr);
          }
        }, 3000);
      } else {
        alert(`Deployment failed: ${response.error}`);
      }
    } catch (err: any) {
      // Handle network errors more gracefully
      if (err.code === 'ECONNABORTED') {
        alert('Request timeout. Deployment may still be in progress. Check back in a few moments.');
      } else {
        alert(`Deployment failed: ${err.response?.data?.error || err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStartWorkers = async (deploymentId: string) => {
    try {
      await supervisorAPI.startWorkers(deploymentId);
      loadDeployments();
    } catch (err: any) {
      alert(`Failed to start workers: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleStopWorkers = async (deploymentId: string) => {
    try {
      await supervisorAPI.stopWorkers(deploymentId);
      loadDeployments();
    } catch (err: any) {
      alert(`Failed to stop workers: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleRestartWorkers = async (deploymentId: string) => {
    try {
      await supervisorAPI.restartWorkers(deploymentId);
      loadDeployments();
    } catch (err: any) {
      alert(`Failed to restart workers: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeleteDeployment = async (deploymentId: string, workerName: string) => {
    if (!confirm(`Are you sure you want to delete deployment "${workerName}"? This will remove all workers.`)) {
      return;
    }

    try {
      await supervisorAPI.deleteDeployment(deploymentId);
      loadDeployments();
    } catch (err: any) {
      alert(`Failed to delete deployment: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdateDockerImage = async (deploymentId: string, workerName: string) => {
    if (!confirm(`Are you sure you want to update the Docker image for "${workerName}"? This will pull the latest image on the remote worker.`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await supervisorAPI.updateDockerImage(deploymentId);
      if (response.success) {
        alert('Docker image update initiated. Please check logs for progress.');
        loadDeployments();
      } else {
        alert(`Failed to update image: ${response.error}`);
      }
    } catch (err: any) {
      alert(`Failed to update Docker image: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleScaleDeployment = (deploymentId: string, currentCount: number) => {
    setScaleDeploymentId(deploymentId);
    setNewWorkerCount(currentCount);
    setScaleMessage('');
    setShowScaleModal(true);
  };

  const submitScale = async () => {
    if (!scaleDeploymentId || newWorkerCount < 1) {
      alert('Invalid worker count');
      return;
    }

    setIsScaling(true);
    setScaleMessage('Scaling deployment...');

    try {
      const response = await supervisorAPI.scaleDeployment(scaleDeploymentId, newWorkerCount);
      if (response.success) {
        setScaleMessage(`✅ ${response.message}`);
        setTimeout(() => {
          setShowScaleModal(false);
          setScaleDeploymentId(null);
          setNewWorkerCount(1);
          setScaleMessage('');
          setIsScaling(false);
          loadDeployments();
        }, 2000);
      } else {
        setScaleMessage(`❌ Failed: ${response.error}`);
        setIsScaling(false);
      }
    } catch (err: any) {
      setScaleMessage(`❌ Error: ${err.response?.data?.error || err.message}`);
      setIsScaling(false);
    }
  };

  const handleBuildAndPushWorker = async () => {
    setIsBuilding(true);
    setBuildProgress(0);
    setBuildStatus('Starting build...');
    setBuildLogs([]);

    try {
      const response = await supervisorAPI.buildAndPushWorker((progress: number, status: string, log?: string) => {
        setBuildProgress(progress);
        setBuildStatus(status);
        if (log) {
          setBuildLogs(prev => [...prev, log]);
        }
      });

      if (response.success) {
        setBuildProgress(100);
        setBuildStatus('✅ Build and push completed successfully!');
        setTimeout(() => {
          setShowBuildModal(false);
          setIsBuilding(false);
          setBuildProgress(0);
          setBuildStatus('');
          setBuildLogs([]);
        }, 2000);
      } else {
        setBuildStatus(`❌ Build failed: ${response.error}`);
        setIsBuilding(false);
      }
    } catch (err: any) {
      setBuildStatus(`❌ Error: ${err.response?.data?.error || err.message}`);
      setIsBuilding(false);
    }
  };

  const handleViewLogs = async (deployment: Deployment) => {
    setSelectedDeployment(deployment);
    setShowLogsModal(true);
    setLogs([]);
    setLogsStreaming(true);

    try {
      // Close previous event source if exists
      if (eventSource) {
        eventSource.close();
      }

      // Start streaming logs (no container name = all docker-compose logs)
      const newEventSource = supervisorAPI.streamLogs(
        deployment.id,
        '', // Empty string = all docker-compose logs
        (log: string) => {
          setLogs(prev => [...prev, log]);
        },
        (error: string) => {
          setLogs(prev => [...prev, `[Error] ${error}`]);
          setLogsStreaming(false);
        }
      );

      setEventSource(newEventSource);
    } catch (err: any) {
      setLogs([`Error starting log stream: ${err.message}`]);
      setLogsStreaming(false);
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'stopped':
        return 'bg-gray-100 text-gray-800';
      case 'deploying':
        return 'bg-blue-100 text-blue-800';
      case 'error':
      case 'unreachable':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getHealthIcon = (healthStatus: string) => {
    switch (healthStatus) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'degraded':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case 'unhealthy':
      case 'unreachable':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-600" />;
    }
  };

  if (loading && deployments.length === 0) {
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
            <h2 className="text-2xl font-bold text-gray-900">Remote Worker Supervisor</h2>
            <p className="text-sm text-gray-600 mt-1">
              Manage remote OCR workers via SSH
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
              onClick={loadDeployments}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Refresh
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Deployment
            </button>
            <button
              onClick={() => setShowBuildModal(true)}
              className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
              title="Build and push worker image to registry"
            >
              <Upload className="w-4 h-4 mr-2" />
              Build & Push Worker
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Server className="w-8 h-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Deployments</p>
                <p className="text-2xl font-bold text-gray-900">{deployments.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="w-8 h-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Running</p>
                <p className="text-2xl font-bold text-gray-900">
                  {deployments.filter(d => d.status === 'running').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Degraded</p>
                <p className="text-2xl font-bold text-gray-900">
                  {deployments.filter(d => d.health_status === 'degraded').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Workers</p>
                <p className="text-2xl font-bold text-gray-900">
                  {deployments.reduce((sum, d) => sum + d.worker_count, 0)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Deployments Table */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Deployments</h3>
          </div>

          {deployments.length === 0 ? (
            <div className="text-center py-12">
              <Server className="w-16 h-16 mx-auto text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">No deployments</h3>
              <p className="mt-2 text-sm text-gray-500">
                Click "Add Deployment" to deploy your first remote worker
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Worker Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Host
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Health
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Workers
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Containers
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {deployments.map((deployment) => (
                    <tr key={deployment.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{deployment.worker_name}</div>
                        <div className="text-sm text-gray-500">{deployment.worker_id}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {deployment.host}:{deployment.port}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(deployment.status)}`}>
                          {deployment.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getHealthIcon(deployment.health_status)}
                          <span className="text-sm text-gray-900">{deployment.health_status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {deployment.worker_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {deployment.containers.filter(c => c.status === 'running').length} / {deployment.containers.length}
                      </td>
                      <td className="px-6 py-4 text-right text-sm font-medium">
                        <div className="flex justify-end gap-3 flex-wrap">
                          {deployment.status === 'stopped' && (
                            <button
                              onClick={() => handleStartWorkers(deployment.id)}
                              className="text-green-600 hover:text-green-900 p-1"
                              title="Start"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          {deployment.status === 'running' && (
                            <button
                              onClick={() => handleStopWorkers(deployment.id)}
                              className="text-yellow-600 hover:text-yellow-900 p-1"
                              title="Stop"
                            >
                              <Square className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleRestartWorkers(deployment.id)}
                            className="text-blue-600 hover:text-blue-900 p-1"
                            title="Restart"
                          >
                            <RotateCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleScaleDeployment(deployment.id, deployment.worker_count)}
                            className="text-orange-600 hover:text-orange-900 p-1"
                            title="Scale Workers"
                          >
                            <Maximize2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleUpdateDockerImage(deployment.id, deployment.worker_name)}
                            className="text-indigo-600 hover:text-indigo-900 p-1"
                            title="Update Docker Image"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleViewLogs(deployment)}
                            className="text-purple-600 hover:text-purple-900 p-1"
                            title="View Logs"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteDeployment(deployment.id, deployment.worker_name)}
                            className="text-red-600 hover:text-red-900 p-1"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      {/* Add Deployment Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Add Worker Deployment</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateDeployment}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Worker Name</label>
                  <input
                    type="text"
                    value={formData.worker_name}
                    onChange={(e) => setFormData({ ...formData, worker_name: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Host (IP Address)</label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Port</label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Username</label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">SSH Key</label>
                    <select
                      value={formData.ssh_key_name}
                      onChange={(e) => setFormData({ ...formData, ssh_key_name: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                      required
                    >
                      <option value="">Select SSH Key</option>
                      {sshKeys.map(key => (
                        <option key={key} value={key}>{key}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Worker Count</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.worker_count}
                    onChange={(e) => setFormData({ ...formData, worker_count: parseInt(e.target.value) })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">NSQ Daemon Address</label>
                  <input
                    type="text"
                    value={formData.nsqd_address}
                    onChange={(e) => setFormData({ ...formData, nsqd_address: e.target.value })}
                    placeholder="e.g., 10.0.0.5:4150"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">NSQ Lookupd Address</label>
                  <input
                    type="text"
                    value={formData.nsqlookupd_addresses[0]}
                    onChange={(e) => setFormData({ ...formData, nsqlookupd_addresses: [e.target.value] })}
                    placeholder="e.g., 10.0.0.5:4161"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">MongoDB URI</label>
                  <input
                    type="text"
                    value={formData.mongo_uri}
                    onChange={(e) => setFormData({ ...formData, mongo_uri: e.target.value })}
                    placeholder="e.g., mongodb://10.0.0.5:27017/gvpocr"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Server URL</label>
                  <input
                    type="text"
                    value={formData.server_url}
                    onChange={(e) => setFormData({ ...formData, server_url: e.target.value })}
                    placeholder="e.g., http://10.0.0.5:5000"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">OCR Providers</label>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.providers.google_vision_enabled}
                        onChange={(e) => setFormData({
                          ...formData,
                          providers: { ...formData.providers, google_vision_enabled: e.target.checked }
                        })}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-700">Google Vision</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.providers.tesseract_enabled}
                        onChange={(e) => setFormData({
                          ...formData,
                          providers: { ...formData.providers, tesseract_enabled: e.target.checked }
                        })}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-gray-700">Tesseract</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Deploying...' : 'Deploy Worker'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Logs Modal */}
      {showLogsModal && selectedDeployment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-medium text-gray-900">
                  Logs - {selectedDeployment.worker_name}
                </h3>
                {logsStreaming && (
                  <div className="flex items-center gap-1">
                    <Activity className="w-4 h-4 text-green-500 animate-spin" />
                    <span className="text-sm text-green-600">Streaming...</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => {
                  setShowLogsModal(false);
                  if (eventSource) {
                    eventSource.close();
                    setEventSource(null);
                  }
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 bg-gray-900 text-green-400 p-4 rounded font-mono text-sm overflow-y-auto border border-gray-700">
              {logs.length === 0 ? (
                <div className="text-gray-500">Waiting for logs...</div>
              ) : (
                logs.map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap break-words">
                    {line}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setLogs([]);
                  setLogsStreaming(true);
                  handleViewLogs(selectedDeployment);
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
              >
                Refresh
              </button>
              <button
                onClick={() => {
                  setShowLogsModal(false);
                  if (eventSource) {
                    eventSource.close();
                    setEventSource(null);
                  }
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Build and Push Worker Modal */}
      {showBuildModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-medium text-gray-900">Build and Push Worker Image</h3>
              <button
                onClick={() => {
                  setShowBuildModal(false);
                  if (!isBuilding) {
                    setBuildProgress(0);
                    setBuildStatus('');
                  }
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-700 mb-3">
                  This will build the latest worker Docker image and push it to the registry.
                </p>
              </div>

              {isBuilding && (
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Progress</span>
                      <span className="text-sm text-gray-600">{buildProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-600 h-full transition-all duration-300"
                        style={{ width: `${buildProgress}%` }}
                      />
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded border border-gray-200">
                    <p className="text-sm text-gray-700 font-mono">{buildStatus}</p>
                  </div>
                  {buildLogs.length > 0 && (
                    <div className="bg-gray-900 text-gray-100 p-3 rounded text-xs max-h-48 overflow-y-auto font-mono">
                      {buildLogs.map((log, idx) => (
                        <div key={idx} className="text-gray-400">{log}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!isBuilding && buildStatus && (
                <div className={`p-4 rounded ${buildStatus.includes('✅') ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <p className={`text-sm font-medium ${buildStatus.includes('✅') ? 'text-green-800' : 'text-red-800'}`}>
                    {buildStatus}
                  </p>
                </div>
              )}

              <div className="border-t pt-4 mt-4">
                <p className="text-sm font-medium text-gray-700 mb-3">Manual Build and Push Commands:</p>
                <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-xs space-y-3 overflow-x-auto">
                  <div>
                    <p className="text-gray-400 mb-1"># Build the worker image</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 break-all">docker build -f worker.Dockerfile -t registry.docgenai.com:5010/gvpocr-worker-updated:latest .</code>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText('docker build -f worker.Dockerfile -t registry.docgenai.com:5010/gvpocr-worker-updated:latest .');
                        }}
                        className="text-blue-400 hover:text-blue-300 whitespace-nowrap text-xs"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                  <div>
                    <p className="text-gray-400 mb-1"># Push to registry</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 break-all">docker push registry.docgenai.com:5010/gvpocr-worker-updated:latest</code>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText('docker push registry.docgenai.com:5010/gvpocr-worker-updated:latest');
                        }}
                        className="text-blue-400 hover:text-blue-300 whitespace-nowrap text-xs"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowBuildModal(false);
                  setBuildProgress(0);
                  setBuildStatus('');
                }}
                disabled={isBuilding}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Close
              </button>
              <button
                onClick={handleBuildAndPushWorker}
                disabled={isBuilding}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                {isBuilding ? 'Building...' : 'Start Build & Push'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scale Deployment Modal */}
      {showScaleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-medium text-gray-900">Scale Workers</h3>
              <button
                onClick={() => {
                  setShowScaleModal(false);
                  setScaleDeploymentId(null);
                  setNewWorkerCount(1);
                  setScaleMessage('');
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {!scaleMessage && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Number of Workers
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      value={newWorkerCount}
                      onChange={(e) => setNewWorkerCount(parseInt(e.target.value) || 1)}
                      disabled={isScaling}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                  <p className="text-sm text-gray-600">
                    This will add or remove worker containers as needed to reach the target count.
                  </p>
                </>
              )}

              {scaleMessage && (
                <div className={`p-4 rounded ${scaleMessage.includes('✅') ? 'bg-green-50 border border-green-200' : scaleMessage.includes('❌') ? 'bg-red-50 border border-red-200' : 'bg-blue-50 border border-blue-200'}`}>
                  <p className={`text-sm font-medium ${scaleMessage.includes('✅') ? 'text-green-800' : scaleMessage.includes('❌') ? 'text-red-800' : 'text-blue-800'}`}>
                    {scaleMessage}
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowScaleModal(false);
                  setScaleDeploymentId(null);
                  setNewWorkerCount(1);
                  setScaleMessage('');
                }}
                disabled={isScaling}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Close
              </button>
              <button
                onClick={submitScale}
                disabled={isScaling}
                className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Maximize2 className="w-4 h-4" />
                {isScaling ? 'Scaling...' : 'Scale'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SupervisorDashboard;
