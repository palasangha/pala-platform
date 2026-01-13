import React, { useState, useEffect } from 'react';
import api from '@/services/api';
import {
  RefreshCw, Plus, Trash2, Play, Square, RotateCw,
  CheckCircle, XCircle, AlertTriangle, Server, Activity, Zap
} from 'lucide-react';

interface SwarmNode {
  id: string;
  hostname: string;
  status: string;
  availability: string;
  manager_status?: string;
  is_manager: boolean;
  ip_address: string;
  engine_version: string;
}

interface SwarmService {
  id: string;
  name: string;
  mode: string;
  replicas: number;
  desired_count: number;
  running_count: number;
  image: string;
  created_at: string;
  updated_at: string;
}

interface SwarmTask {
  id: string;
  service_id: string;
  service_name: string;
  node_id: string;
  hostname: string;
  status: string;
  state: string;
  error?: string;
}

interface SwarmInfo {
  swarm_id: string;
  is_manager: boolean;
  is_active: boolean;
  node_count: number;
  manager_count: number;
  worker_count: number;
  version: string;
}

interface HealthStatus {
  swarm: SwarmInfo;
  nodes: {
    total: number;
    ready: number;
    unhealthy: number;
    list: SwarmNode[];
  };
  is_healthy: boolean;
}

export const SwarmDashboard: React.FC = () => {
  const [nodes, setNodes] = useState<SwarmNode[]>([]);
  const [services, setServices] = useState<SwarmService[]>([]);
  const [tasks, setTasks] = useState<SwarmTask[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [swarmInitialized, setSwarmInitialized] = useState(false);

  // Modal states
  const [showCreateServiceModal, setShowCreateServiceModal] = useState(false);
  const [showScaleModal, setShowScaleModal] = useState(false);
  const [selectedService, setSelectedService] = useState<SwarmService | null>(null);
  const [newReplicas, setNewReplicas] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);

  // Create service form
  const [serviceName, setServiceName] = useState('');
  const [serviceImage, setServiceImage] = useState('');
  const [serviceReplicas, setServiceReplicas] = useState(1);

  // Remote worker launch form
  const [showRemoteWorkerModal, setShowRemoteWorkerModal] = useState(false);
  const [remoteWorkerForm, setRemoteWorkerForm] = useState({
    host: '',
    username: '',
    password: '',
    docker_image: 'registry.docgenai.com:5010/gvpocr-worker-updated:latest',
    worker_name: '',
    replica_count: 1
  });

  // Active tab
  const [activeTab, setActiveTab] = useState<'overview' | 'nodes' | 'services' | 'tasks'>('overview');

  const loadSwarmData = async () => {
    try {
      setLoading(true);
      const [nodesRes, servicesRes, tasksRes, healthRes] = await Promise.all([
        api.get('/swarm/nodes').catch(() => ({ data: { data: [] } })),
        api.get('/swarm/services').catch(() => ({ data: { data: [] } })),
        api.get('/swarm/tasks').catch(() => ({ data: { data: [] } })),
        api.get('/swarm/health').catch(() => ({ data: null })),
      ]);

      console.log('[DEBUG] Nodes response:', nodesRes.data);
      console.log('[DEBUG] Services response:', servicesRes.data);
      console.log('[DEBUG] Tasks response:', tasksRes.data);
      console.log('[DEBUG] Health response:', healthRes.data);

      const servicesData = servicesRes.data?.data || [];
      const nodesData = nodesRes.data?.data || [];
      const tasksData = tasksRes.data?.data || [];
      
      console.log('[DEBUG] Setting nodes:', nodesData.length);
      console.log('[DEBUG] Setting services:', servicesData.length, servicesData);
      console.log('[DEBUG] Setting tasks:', tasksData.length);
      
      setNodes(nodesData);
      setServices(servicesData);
      setTasks(tasksData);
      
      if (healthRes.data) {
        setHealth(healthRes.data);
        setSwarmInitialized(true);
      }
      setError('');
    } catch (err: any) {
      console.error('[DEBUG] Error loading swarm data:', err);
      setError(err.response?.data?.error || 'Failed to load Swarm data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSwarmData();
  }, []);

  useEffect(() => {
    console.log('[DEBUG] Services state updated:', services);
    if (services.length > 0 && activeTab === 'overview') {
      console.log('[DEBUG] Auto-switching to services tab - found', services.length, 'services');
      setActiveTab('services');
    }
  }, [services]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadSwarmData, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const handleScaleService = async (serviceId: string, newCount: number) => {
    try {
      setIsProcessing(true);
      await api.post(`/swarm/services/${serviceId}/scale`, {
        replicas: newCount,
      });
      await loadSwarmData();
      setShowScaleModal(false);
      setSelectedService(null);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to scale service');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCreateService = async () => {
    try {
      setIsProcessing(true);
      let imageUrl = serviceImage.trim();
      // Strip scheme from image URL if present
      imageUrl = imageUrl.replace(/^https?:\/\//, '');
      
      await api.post('/swarm/services', {
        name: serviceName,
        image: imageUrl,
        replicas: serviceReplicas,
      });
      await loadSwarmData();
      setShowCreateServiceModal(false);
      setServiceName('');
      setServiceImage('');
      setServiceReplicas(1);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to create service');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRemoveService = async (serviceId: string) => {
    if (!confirm('Are you sure you want to remove this service?')) return;

    try {
      setIsProcessing(true);
      await api.delete(`/swarm/services/${serviceId}`);
      await loadSwarmData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to remove service');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLaunchRemoteWorker = async () => {
    try {
      setIsProcessing(true);
      await api.post('/swarm/launch-remote-worker', {
        host: remoteWorkerForm.host,
        username: remoteWorkerForm.username,
        password: remoteWorkerForm.password,
        docker_image: remoteWorkerForm.docker_image,
        worker_name: remoteWorkerForm.worker_name || `worker-${remoteWorkerForm.host}`,
        replica_count: remoteWorkerForm.replica_count,
      });
      
      setShowRemoteWorkerModal(false);
      setRemoteWorkerForm({
        host: '',
        username: '',
        password: '',
        docker_image: 'registry.docgenai.com:5010/gvpocr-worker-updated:latest',
        worker_name: '',
        replica_count: 1
      });
      
      setError('');
      // Reload swarm data after a delay to allow node to register
      setTimeout(() => loadSwarmData(), 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to launch remote worker');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDrainNode = async (nodeId: string) => {
    if (!confirm('Are you sure you want to drain this node?')) return;

    try {
      setIsProcessing(true);
      await api.post(`/swarm/nodes/${nodeId}/drain`);
      await loadSwarmData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to drain node');
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePromoteNode = async (nodeId: string) => {
    try {
      setIsProcessing(true);
      await api.post(`/swarm/nodes/${nodeId}/promote`);
      await loadSwarmData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to promote node');
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'ready':
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
      case 'down':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
      case 'running':
        return <CheckCircle className="w-4 h-4" />;
      case 'failed':
      case 'down':
        return <XCircle className="w-4 h-4" />;
      case 'pending':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  if (loading && !swarmInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Swarm data...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Refresh Controls */}
      <div className="flex items-center gap-3 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Docker Swarm</h1>
          <p className="text-sm text-gray-500">Monitor and manage your cluster</p>
        </div>
        <div className="flex items-center gap-3 ml-auto">
          <button
            onClick={() => {
              setAutoRefresh(!autoRefresh);
            }}
            className={`p-2 rounded-lg transition-colors ${
              autoRefresh
                ? 'bg-blue-100 text-blue-600'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
          >
            <RefreshCw className={`w-5 h-5 ${autoRefresh ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => loadSwarmData()}
            className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
            disabled={isProcessing}
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Health Status Alert */}
      {health && health.nodes && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              health.is_healthy
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-red-50 border-red-200 text-red-800'
            }`}
          >
            <div className="flex items-center gap-3">
              {health.is_healthy ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <XCircle className="w-5 h-5" />
              )}
              <div>
                <h3 className="font-semibold">
                  {health.is_healthy ? 'Cluster Healthy' : 'Cluster Unhealthy'}
                </h3>
                <p className="text-sm opacity-90">
                  {health.nodes.ready || 0}/{health.nodes.total || 0} nodes ready
                  {(health.nodes.unhealthy || 0) > 0 && ` - ${health.nodes.unhealthy} unhealthy`}
                </p>
              </div>
            </div>
          </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-lg">
          <p className="font-semibold">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Statistics Cards */}
      {health && health.nodes && health.swarm && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Total Nodes</p>
                 <p className="text-3xl font-bold text-gray-900 mt-2">
                   {health.nodes.total || 0}
                 </p>
              </div>
              <Server className="w-12 h-12 text-blue-100" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Managers</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {health.swarm.manager_count || 0}
                </p>
              </div>
              <Activity className="w-12 h-12 text-green-100" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Workers</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {health.swarm.worker_count || 0}
                </p>
              </div>
              <Zap className="w-12 h-12 text-yellow-100" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm font-medium">Services</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {services.length}
                </p>
              </div>
              <Plus className="w-12 h-12 text-purple-100" />
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <div className="flex">
            {(['overview', 'nodes', 'services', 'tasks'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-4 font-medium text-sm transition-colors ${
                  activeTab === tab
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && health && health.nodes && health.swarm && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Cluster Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-500 text-sm">Swarm ID</p>
                    <p className="text-gray-900 font-mono text-sm mt-1 break-all">
                      {health.swarm?.swarm_id?.substring(0, 12) || 'N/A'}...
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-500 text-sm">Version</p>
                    <p className="text-gray-900 font-mono text-sm mt-1">
                      {health.swarm?.version || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Node Status</h3>
                <div className="space-y-2">
                  {(health.nodes.list || []).slice(0, 5).map((node) => (
                    <div
                      key={node.id}
                      className="flex items-center justify-between bg-gray-50 rounded-lg p-4"
                    >
                      <div className="flex items-center gap-3">
                        {getStatusIcon(node.status)}
                        <div>
                          <p className="font-medium text-gray-900">{node.hostname}</p>
                          <p className="text-sm text-gray-500">{node.ip_address}</p>
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(node.status)}`}>
                        {node.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Nodes Tab */}
          {activeTab === 'nodes' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Cluster Nodes</h3>
                <button
                  onClick={() => setShowRemoteWorkerModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                  disabled={isProcessing}
                >
                  <Plus className="w-4 h-4" />
                  Add Remote Worker
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hostname</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Availability</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {nodes.map((node) => (
                      <tr key={node.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <p className="font-medium text-gray-900">{node.hostname}</p>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(node.status)}`}>
                            {node.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded text-sm font-medium ${
                            node.is_manager
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {node.is_manager ? 'Manager' : 'Worker'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {node.availability}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-gray-600">
                          {node.ip_address}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleDrainNode(node.id)}
                              disabled={isProcessing}
                              className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
                              title="Drain node"
                            >
                              <Square className="w-4 h-4 text-orange-600" />
                            </button>
                            {!node.is_manager && (
                              <button
                                onClick={() => handlePromoteNode(node.id)}
                                disabled={isProcessing}
                                className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
                                title="Promote to manager"
                              >
                                <Play className="w-4 h-4 text-green-600" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Services Tab */}
          {activeTab === 'services' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Services</h3>
                <button
                  onClick={() => setShowCreateServiceModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  disabled={isProcessing}
                >
                  <Plus className="w-4 h-4" />
                  Create Service
                </button>
              </div>

              {services.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500">No services deployed yet</p>
                  <p className="text-sm text-gray-400 mt-2">Create a service to get started</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Service Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Image</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mode</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Replicas</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {services.map((service) => (
                      <tr key={service.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <p className="font-medium text-gray-900">{service.name}</p>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-gray-600">
                          {service.image.substring(0, 40)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {service.mode}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">
                            {service.running_count}/{service.desired_count}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                            service.running_count === service.desired_count
                              ? 'bg-green-100 text-green-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {service.running_count === service.desired_count ? 'Running' : 'Updating'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                setSelectedService(service);
                                setNewReplicas(service.desired_count);
                                setShowScaleModal(true);
                              }}
                              disabled={isProcessing}
                              className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
                              title="Scale service"
                            >
                              <RotateCw className="w-4 h-4 text-blue-600" />
                            </button>
                            <button
                              onClick={() => handleRemoveService(service.id)}
                              disabled={isProcessing}
                              className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
                              title="Remove service"
                            >
                              <Trash2 className="w-4 h-4 text-red-600" />
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
          )}

          {/* Tasks Tab */}
          {activeTab === 'tasks' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Tasks</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Service</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Node</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {tasks.map((task) => (
                      <tr key={task.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {task.service_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {task.hostname}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(task.status)}`}>
                            {task.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {task.state}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Service Modal */}
      {showCreateServiceModal && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Create Service</h2>
            <button
              onClick={() => setShowCreateServiceModal(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Service Name
              </label>
              <input
                type="text"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="my-service"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Image
              </label>
              <input
                type="text"
                value={serviceImage}
                onChange={(e) => setServiceImage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="registry.example.com:5000/image:latest"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Replicas
              </label>
              <input
                type="number"
                min="1"
                value={serviceReplicas}
                onChange={(e) => setServiceReplicas(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex gap-3 p-6 border-t border-gray-200">
            <button
              onClick={() => setShowCreateServiceModal(false)}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateService}
              disabled={isProcessing || !serviceName || !serviceImage}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isProcessing ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      </div>
      )}

      {/* Scale Service Modal */}
      {showScaleModal && selectedService && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Scale Service</h2>
            <button
              onClick={() => {
                setShowScaleModal(false);
                setSelectedService(null);
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="p-6 space-y-4">
            <p className="text-gray-600">
              Scaling service <strong>{selectedService.name}</strong>
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Desired Replicas
              </label>
              <input
                type="number"
                min="1"
                value={newReplicas}
                onChange={(e) => setNewReplicas(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex gap-3 p-6 border-t border-gray-200">
            <button
              onClick={() => {
                setShowScaleModal(false);
                setSelectedService(null);
              }}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => handleScaleService(selectedService.id, newReplicas)}
              disabled={isProcessing}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isProcessing ? 'Scaling...' : 'Scale'}
            </button>
          </div>
        </div>
      </div>
      )}

      {/* Remote Worker Launch Modal */}
      {showRemoteWorkerModal && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Add Remote Worker</h2>
            <button
              onClick={() => setShowRemoteWorkerModal(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Host IP Address
              </label>
              <input
                type="text"
                value={remoteWorkerForm.host}
                onChange={(e) => setRemoteWorkerForm({...remoteWorkerForm, host: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="172.12.0.83"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SSH Username
              </label>
              <input
                type="text"
                value={remoteWorkerForm.username}
                onChange={(e) => setRemoteWorkerForm({...remoteWorkerForm, username: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="tod"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SSH Password
              </label>
              <input
                type="password"
                value={remoteWorkerForm.password}
                onChange={(e) => setRemoteWorkerForm({...remoteWorkerForm, password: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="••••••••"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Docker Image
              </label>
              <input
                type="text"
                value={remoteWorkerForm.docker_image}
                onChange={(e) => setRemoteWorkerForm({...remoteWorkerForm, docker_image: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="registry.docgenai.com:5010/gvpocr-worker-updated:latest"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Worker Name (optional)
              </label>
              <input
                type="text"
                value={remoteWorkerForm.worker_name}
                onChange={(e) => setRemoteWorkerForm({...remoteWorkerForm, worker_name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="worker-name"
              />
            </div>
          </div>

          <div className="flex gap-3 p-6 border-t border-gray-200">
            <button
              onClick={() => setShowRemoteWorkerModal(false)}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleLaunchRemoteWorker}
              disabled={isProcessing || !remoteWorkerForm.host || !remoteWorkerForm.username || !remoteWorkerForm.password}
              className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {isProcessing ? 'Launching...' : 'Launch Worker'}
            </button>
          </div>
        </div>
      </div>
      )}
    </div>
  );
};
