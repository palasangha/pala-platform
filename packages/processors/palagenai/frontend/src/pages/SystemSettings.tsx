import React, { useState, useEffect } from 'react';
import { Server, RefreshCw, Settings, Copy, Check, AlertCircle, Download, Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

const SystemSettings: React.FC = () => {
  const token = useAuthStore((state) => state.accessToken);
  const [status, setStatus] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);
  const [envVariables, setEnvVariables] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [restarting, setRestarting] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editValues, setEditValues] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [showSensitive, setShowSensitive] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    fetchSystemInfo();
    const interval = setInterval(fetchSystemInfo, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchSystemInfo = async () => {
    try {
      const [statusRes, configRes, envRes] = await Promise.all([
        fetch('/api/system/status', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('/api/system/config', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('/api/system/env-variables', {
          headers: { 'Authorization': `Bearer ${token}` }
        }).catch(() => null)
      ]);

      if (statusRes.ok) {
        const data = await statusRes.json();
        setStatus(data.status);
      }

      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(data.config);
        setEditValues(data.config);
      }

      if (envRes && envRes.ok) {
        const data = await envRes.json();
        // data.variables now contains { value, services, service_count }
        setEnvVariables(data.variables || {});
      }

      setError(null);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch system info');
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const restartService = async (serviceName: string) => {
    setRestarting(serviceName);
    try {
      const response = await fetch('/api/system/restart', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ service: serviceName })
      });

      const data = await response.json();

      if (data.success) {
        alert(`${serviceName} restarted successfully`);
        await new Promise(resolve => setTimeout(resolve, 2000));
        fetchSystemInfo();
      } else {
        alert(`Failed to restart ${serviceName}: ${data.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setRestarting(null);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const updates: any = {};
      const safeSections = ['archipelago', 'docker'];

      for (const section of safeSections) {
        if (editValues[section]) {
          for (const [key, value] of Object.entries(editValues[section])) {
            const envKey = `${section.toUpperCase()}_${key.toUpperCase()}`;
            updates[envKey] = value;
          }
        }
      }

      const response = await fetch('/api/system/env-update', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ updates })
      });

      const data = await response.json();

      if (data.success) {
        alert('Settings saved! Some services may need to be restarted.');
        setEditMode(false);
        fetchSystemInfo();
      } else {
        alert(`Failed to save settings: ${data.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const downloadLogs = async (serviceName: string) => {
    try {
      const response = await fetch(`/api/system/docker-logs/${serviceName}?lines=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await response.json();

      if (data.success) {
        const element = document.createElement('a');
        const file = new Blob([data.logs], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = `${serviceName}-logs.txt`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
      }
    } catch (err) {
      alert(`Error downloading logs: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
          <p>Loading system information...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Main Content */}
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Server className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold">System Settings & Configuration</h1>
        </div>
        <p className="text-gray-600">Manage services, view configuration, and update settings</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600" />
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Service URLs */}
      {status && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Server className="w-5 h-5" />
            Service URLs
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Backend */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="font-medium text-gray-800 mb-2">{status.backend.name}</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">URL:</span>
                  <button
                    onClick={() => copyToClipboard(status.backend.url, 'backend-url')}
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800"
                  >
                    {copied === 'backend-url' ? (
                      <><Check className="w-4 h-4" /> Copied</>
                    ) : (
                      <><Copy className="w-4 h-4" /> {status.backend.url}</>
                    )}
                  </button>
                </div>
                <p className="text-sm text-gray-600">Port: {status.backend.port}</p>
                <p className="text-sm text-gray-600">Environment: {status.backend.debug ? 'Development' : 'Production'}</p>
              </div>
            </div>

            {/* Frontend */}
            <div className="border rounded-lg p-4 bg-gray-50">
              <h3 className="font-medium text-gray-800 mb-2">{status.frontend.name}</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">URL:</span>
                  <button
                    onClick={() => copyToClipboard(status.frontend.url, 'frontend-url')}
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800"
                  >
                    {copied === 'frontend-url' ? (
                      <><Check className="w-4 h-4" /> Copied</>
                    ) : (
                      <><Copy className="w-4 h-4" /> {status.frontend.url}</>
                    )}
                  </button>
                </div>
                <p className="text-sm text-gray-600">Port: {status.frontend.port}</p>
                <p className="text-sm text-gray-600">Environment: {status.frontend.environment}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Docker Running Services */}
      {status && status.running_services && status.running_services.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Server className="w-5 h-5" />
            Running Docker Services ({status.running_services.length})
          </h2>
          <div className="space-y-3">
            {status.running_services.map((service: any, idx: number) => (
              <div key={idx} className="border rounded-lg p-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-800">{service.name}</h3>
                  <p className="text-sm text-gray-600">Image: {service.image}</p>
                  <p className="text-sm text-gray-600">Status: <span className="text-green-700 font-semibold">{service.status}</span></p>
                  <p className="text-sm text-gray-600">Container ID: {service.container_id}</p>
                  {service.ports && <p className="text-sm text-gray-600">Ports: {service.ports || 'None'}</p>}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => downloadLogs(service.name)}
                    className="p-2 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                    title="Download logs"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => restartService(service.name)}
                    disabled={restarting === service.name}
                    className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {restarting === service.name ? (
                      <><RefreshCw className="w-4 h-4 animate-spin" /> Restarting...</>
                    ) : (
                      <><RefreshCw className="w-4 h-4" /> Restart</>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Docker Configured Services from docker-compose.yml */}
      {status && status.configured_services && Object.keys(status.configured_services).length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Configured Services in docker-compose.yml ({Object.keys(status.configured_services).length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.values(status.configured_services).map((service: any, idx: number) => {
              // Check if this service is running
              const isRunning = status.running_services?.some((s: any) => s.name.includes(service.name));
              return (
                <div key={idx} className={`border rounded-lg p-3 ${isRunning ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
                  <h4 className="font-medium text-gray-800">{service.name}</h4>
                  <p className="text-xs text-gray-600 mb-2">Image: {service.image}</p>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      isRunning 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {isRunning ? '🟢 Running' : '⚪ Stopped'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Configuration */}
      {config && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Configuration
            </h2>
            {!editMode ? (
              <button
                onClick={() => setEditMode(true)}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
              >
                Edit Settings
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={saveSettings}
                  disabled={saving}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={() => setEditMode(false)}
                  className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {/* Archipelago Config */}
          <div className="mb-6 border rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-800 mb-3">Archipelago Commons</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                {editMode ? (
                  <input
                    type="text"
                    value={editValues.archipelago?.base_url || ''}
                    onChange={(e) =>
                      setEditValues({
                        ...editValues,
                        archipelago: { ...editValues.archipelago, base_url: e.target.value }
                      })
                    }
                    className="w-full border rounded px-3 py-2"
                  />
                ) : (
                  <p className="text-gray-600">{config.archipelago?.base_url || 'Not configured'}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="block text-sm font-medium text-gray-700">Verify SSL</label>
                {editMode ? (
                  <input
                    type="checkbox"
                    checked={editValues.archipelago?.verify_ssl || false}
                    onChange={(e) =>
                      setEditValues({
                        ...editValues,
                        archipelago: { ...editValues.archipelago, verify_ssl: e.target.checked }
                      })
                    }
                    className="border rounded"
                  />
                ) : (
                  <span className={`px-2 py-1 rounded text-xs ${
                    config.archipelago?.verify_ssl ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {config.archipelago?.verify_ssl ? 'Enabled' : 'Disabled'}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Database Config */}
          <div className="mb-6 border rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-800 mb-3">Database</h3>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                MongoDB: <span className={`px-2 py-1 rounded text-xs ${
                  config.database?.mongodb_connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {config.database?.mongodb_connected ? 'Connected' : 'Disconnected'}
                </span>
              </p>
              <p className="text-sm text-gray-600">Database: {config.database?.mongo_db}</p>
            </div>
          </div>

          {/* Queue Config */}
          <div className="mb-6 border rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-800 mb-3">Message Queue (NSQ)</h3>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                NSQ: <span className={`px-2 py-1 rounded text-xs ${
                  config.queue?.nsq_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {config.queue?.nsq_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </p>
              <p className="text-sm text-gray-600">Address: {config.queue?.nsqd_address}</p>
            </div>
          </div>

          {/* Docker Config */}
          <div className="border rounded-lg p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-800 mb-3">Docker</h3>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                Swarm Mode: <span className={`px-2 py-1 rounded text-xs ${
                  config.docker?.swarm_mode ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {config.docker?.swarm_mode ? 'Enabled' : 'Disabled'}
                </span>
              </p>
              <p className="text-sm text-gray-600">Worker Image: {config.docker?.worker_image}</p>
            </div>
          </div>
        </div>
      )}

      {/* Environment Variables Section */}
      {Object.keys(envVariables).length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Docker Compose Environment Variables
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            View all environment variables from docker-compose.yml file
          </p>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Variable Name</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Value</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Services</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Object.entries(envVariables).map(([key, data]: [string, any]) => {
                  const actualValue = typeof data === 'string' ? data : (data.value || '');
                  const services = typeof data === 'string' ? [] : (data.services || []);

                  const isSensitive = ['PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'API_KEY'].some(
                    sensitive => key.toUpperCase().includes(sensitive)
                  );
                  const isVisible = showSensitive[key] || !isSensitive;
                  const displayValue = isSensitive && !isVisible ? '••••••••' : String(actualValue);

                  return (
                    <tr key={key} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded text-gray-800">
                          {key}
                        </code>
                        {isSensitive && (
                          <span className="ml-2 inline-block px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                            Sensitive
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono bg-gray-50 px-3 py-2 rounded text-gray-700 max-w-xs truncate">
                            {displayValue}
                          </code>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {services.length > 0 ? (
                            services.map((service: string) => (
                              <span key={service} className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                {service}
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-gray-500">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {isSensitive && (
                            <button
                              onClick={() => setShowSensitive({
                                ...showSensitive,
                                [key]: !showSensitive[key]
                              })}
                              className="p-2 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                              title={isVisible ? 'Hide' : 'Show'}
                            >
                              {isVisible ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => copyToClipboard(String(actualValue), `env-${key}`)}
                            className="p-2 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                            title="Copy value"
                          >
                            {copied === `env-${key}` ? (
                              <Check className="w-4 h-4 text-green-600" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-700">
              💡 <strong>Note:</strong> Sensitive variables (passwords, secrets, tokens) are hidden by default for security. Click the eye icon to reveal them.
            </p>
          </div>
        </div>
      )}

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-500">
        <p>Last updated: {new Date().toLocaleTimeString()}</p>
        <p>Refreshes automatically every 30 seconds</p>
      </div>
    </div>
  );
};

export default SystemSettings;
