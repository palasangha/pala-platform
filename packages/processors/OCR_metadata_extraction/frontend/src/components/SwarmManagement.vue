<template>
  <div class="swarm-management">
    <div class="container-fluid">
      <!-- Header -->
      <div class="swarm-header mb-4">
        <h1 class="mb-4">
          <i class="fas fa-docker"></i> Docker Swarm Management
        </h1>

        <!-- Quick Stats -->
        <div class="row mb-4" v-if="swarmInfo">
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-value">{{ swarmInfo.node_count }}</div>
              <div class="stat-label">Nodes</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-value">{{ swarmInfo.manager_count }}</div>
              <div class="stat-label">Managers</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-value">{{ swarmInfo.worker_count }}</div>
              <div class="stat-label">Workers</div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card" :class="{ 'status-healthy': swarmInfo.is_active, 'status-unhealthy': !swarmInfo.is_active }">
              <div class="stat-value">{{ swarmInfo.is_active ? 'Active' : 'Inactive' }}</div>
              <div class="stat-label">Status</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <ul class="nav nav-tabs mb-4" role="tablist">
        <li class="nav-item">
          <a class="nav-link active" data-toggle="tab" href="#services">Services</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" data-toggle="tab" href="#nodes">Nodes</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" data-toggle="tab" href="#health">Health</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" data-toggle="tab" href="#statistics">Statistics</a>
        </li>
      </ul>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Services Tab -->
        <div id="services" class="tab-pane fade show active">
          <h3 class="mb-4">Services</h3>
          
          <!-- Refresh Button -->
          <button class="btn btn-primary mb-3" @click="refreshServices" :disabled="loading">
            <i class="fas fa-sync"></i> {{ loading ? 'Loading...' : 'Refresh' }}
          </button>

          <!-- Services List -->
          <div class="card" v-if="services.length > 0">
            <div class="table-responsive">
              <table class="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Mode</th>
                    <th>Replicas</th>
                    <th>Running</th>
                    <th>Image</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="service in services" :key="service.id">
                    <td><strong>{{ service.name }}</strong></td>
                    <td>{{ service.mode }}</td>
                    <td>{{ service.replicas }}</td>
                    <td>
                      <span :class="{ 'badge badge-success': service.running_count === service.desired_count, 'badge badge-warning': service.running_count < service.desired_count }">
                        {{ service.running_count }}/{{ service.desired_count }}
                      </span>
                    </td>
                    <td><small>{{ service.image }}</small></td>
                    <td>
                      <span v-if="service.running_count === service.desired_count" class="badge badge-success">
                        Healthy
                      </span>
                      <span v-else class="badge badge-danger">
                        Degraded
                      </span>
                    </td>
                    <td>
                      <button class="btn btn-sm btn-info" @click="showScaleModal(service)" title="Scale">
                        <i class="fas fa-expand"></i>
                      </button>
                      <button class="btn btn-sm btn-warning" @click="showLogsModal(service)" title="Logs">
                        <i class="fas fa-file-alt"></i>
                      </button>
                      <button class="btn btn-sm btn-danger" @click="removeService(service.name)" title="Remove">
                        <i class="fas fa-trash"></i>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="alert alert-info">
            <i class="fas fa-info-circle"></i> No services found
          </div>
        </div>

        <!-- Nodes Tab -->
        <div id="nodes" class="tab-pane fade">
          <h3 class="mb-4">Nodes</h3>
          
          <button class="btn btn-primary mb-3" @click="refreshNodes" :disabled="loading">
            <i class="fas fa-sync"></i> {{ loading ? 'Loading...' : 'Refresh' }}
          </button>

          <div class="card" v-if="nodes.length > 0">
            <div class="table-responsive">
              <table class="table table-hover mb-0">
                <thead>
                  <tr>
                    <th>Hostname</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Availability</th>
                    <th>IP Address</th>
                    <th>Engine Version</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="node in nodes" :key="node.id">
                    <td><strong>{{ node.hostname }}</strong></td>
                    <td>
                      <span v-if="node.is_manager" class="badge badge-primary">Manager</span>
                      <span v-else class="badge badge-secondary">Worker</span>
                    </td>
                    <td>
                      <span :class="{ 'badge badge-success': node.status === 'ready', 'badge badge-danger': node.status !== 'ready' }">
                        {{ node.status }}
                      </span>
                    </td>
                    <td>
                      <span :class="{ 'badge badge-success': node.availability === 'active', 'badge badge-warning': node.availability === 'pause', 'badge badge-danger': node.availability === 'drain' }">
                        {{ node.availability }}
                      </span>
                    </td>
                    <td><code>{{ node.ip_address }}</code></td>
                    <td>{{ node.engine_version }}</td>
                    <td>
                      <div class="btn-group btn-group-sm" v-if="node.availability === 'active'">
                        <button class="btn btn-warning" @click="drainNode(node.id)" title="Drain for maintenance">
                          <i class="fas fa-pause"></i>
                        </button>
                        <button class="btn btn-danger" @click="removeNode(node.id)" title="Remove node">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                      <button class="btn btn-sm btn-success" v-else @click="restoreNode(node.id)" title="Restore node">
                        <i class="fas fa-play"></i> Restore
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="alert alert-info">
            <i class="fas fa-info-circle"></i> No nodes found
          </div>
        </div>

        <!-- Health Tab -->
        <div id="health" class="tab-pane fade">
          <h3 class="mb-4">Health Status</h3>
          
          <button class="btn btn-primary mb-3" @click="refreshHealth" :disabled="loading">
            <i class="fas fa-sync"></i> {{ loading ? 'Loading...' : 'Refresh' }}
          </button>

          <div v-if="health" class="row">
            <!-- Overall Health -->
            <div class="col-md-12 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Overall Status</h5>
                  <div class="alert" :class="{ 'alert-success': health.overall_health === 'healthy', 'alert-warning': health.overall_health === 'degraded', 'alert-danger': health.overall_health === 'unhealthy' }">
                    <strong>{{ health.overall_health.toUpperCase() }}</strong>
                  </div>
                </div>
              </div>
            </div>

            <!-- Node Health -->
            <div class="col-md-6 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Nodes</h5>
                  <p class="mb-1">Total: {{ health.nodes.total }}</p>
                  <p class="mb-1"><span class="badge badge-success">Ready: {{ health.nodes.ready }}</span></p>
                  <p class="mb-0"><span class="badge badge-danger">Unhealthy: {{ health.nodes.unhealthy }}</span></p>
                </div>
              </div>
            </div>

            <!-- Service Health -->
            <div class="col-md-6 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Services</h5>
                  <p class="mb-1">Total: {{ health.services.total }}</p>
                  <p class="mb-1"><span class="badge badge-success">Healthy: {{ health.services.healthy }}</span></p>
                  <p class="mb-0"><span class="badge badge-danger">Unhealthy: {{ health.services.unhealthy }}</span></p>
                </div>
              </div>
            </div>

            <!-- Detailed Node Status -->
            <div class="col-md-12">
              <div class="card">
                <div class="card-header">
                  <h5 class="mb-0">Node Details</h5>
                </div>
                <div class="table-responsive">
                  <table class="table table-sm mb-0">
                    <thead>
                      <tr>
                        <th>Hostname</th>
                        <th>Status</th>
                        <th>Availability</th>
                        <th>Role</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="node in health.nodes.list" :key="node.id">
                        <td>{{ node.hostname }}</td>
                        <td><span :class="{ 'badge badge-success': node.status === 'ready', 'badge badge-danger': node.status !== 'ready' }">{{ node.status }}</span></td>
                        <td><span class="badge" :class="{ 'badge-success': node.availability === 'active', 'badge-warning': node.availability === 'pause', 'badge-danger': node.availability === 'drain' }">{{ node.availability }}</span></td>
                        <td><span class="badge" :class="{ 'badge-primary': node.is_manager, 'badge-secondary': !node.is_manager }">{{ node.is_manager ? 'Manager' : 'Worker' }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Statistics Tab -->
        <div id="statistics" class="tab-pane fade">
          <h3 class="mb-4">Statistics</h3>
          
          <button class="btn btn-primary mb-3" @click="refreshStatistics" :disabled="loading">
            <i class="fas fa-sync"></i> {{ loading ? 'Loading...' : 'Refresh' }}
          </button>

          <div v-if="statistics" class="row">
            <!-- Cluster Stats -->
            <div class="col-md-4 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Cluster</h5>
                  <p class="mb-1"><strong>Nodes:</strong> {{ statistics.cluster.node_count }}</p>
                  <p class="mb-1"><strong>Managers:</strong> {{ statistics.cluster.manager_count }}</p>
                  <p class="mb-0"><strong>Workers:</strong> {{ statistics.cluster.worker_count }}</p>
                </div>
              </div>
            </div>

            <!-- Services Stats -->
            <div class="col-md-4 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Services</h5>
                  <p class="mb-1"><strong>Total:</strong> {{ statistics.services.total }}</p>
                  <p class="mb-1"><strong>Total Replicas:</strong> {{ statistics.services.total_replicas }}</p>
                  <p class="mb-0"><strong>Running:</strong> {{ statistics.services.running_replicas }}</p>
                </div>
              </div>
            </div>

            <!-- Tasks Stats -->
            <div class="col-md-4 mb-4">
              <div class="card">
                <div class="card-body">
                  <h5 class="card-title">Tasks</h5>
                  <p class="mb-1"><strong>Total:</strong> {{ statistics.tasks.total }}</p>
                  <p class="mb-1"><strong>Running:</strong> {{ statistics.tasks.running }}</p>
                  <p class="mb-0"><strong>Failed:</strong> {{ statistics.tasks.failed }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Scale Service Modal -->
    <div class="modal fade" id="scaleModal" tabindex="-1" role="dialog">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Scale Service</h5>
            <button type="button" class="close" data-dismiss="modal">
              <span>&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <div v-if="selectedService" class="form-group">
              <label>Service: <strong>{{ selectedService.name }}</strong></label>
              <label for="replicasInput" class="mt-3">Number of Replicas:</label>
              <input type="number" class="form-control" id="replicasInput" v-model.number="replicasInput" min="0" max="100">
              <small class="form-text text-muted">Current: {{ selectedService.replicas }}</small>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" @click="scaleService" :disabled="loading">Scale</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs Modal -->
    <div class="modal fade" id="logsModal" tabindex="-1" role="dialog">
      <div class="modal-dialog modal-lg" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Service Logs - {{ selectedService ? selectedService.name : '' }}</h5>
            <button type="button" class="close" data-dismiss="modal">
              <span>&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <div class="alert alert-info" v-if="!serviceLogs.length">
              Loading logs...
            </div>
            <div v-else class="logs-container" style="max-height: 400px; overflow-y: auto;">
              <pre v-for="(log, index) in serviceLogs" :key="index" class="mb-1">{{ log }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <div class="toast-container">
      <div v-for="toast in toasts" :key="toast.id" class="toast" :class="{ 'toast-success': toast.type === 'success', 'toast-error': toast.type === 'error' }">
        {{ toast.message }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SwarmManagement',
  data() {
    return {
      loading: false,
      swarmInfo: null,
      services: [],
      nodes: [],
      health: null,
      statistics: null,
      serviceLogs: [],
      selectedService: null,
      replicasInput: 0,
      toasts: []
    }
  },
  mounted() {
    this.loadData();
    // Refresh every 30 seconds
    setInterval(() => {
      this.loadData();
    }, 30000);
  },
  methods: {
    async loadData() {
      await Promise.all([
        this.refreshServices(),
        this.refreshNodes(),
        this.refreshHealth(),
        this.refreshStatistics()
      ]);
    },
    async refreshServices() {
      this.loading = true;
      try {
        const response = await fetch('/api/swarm/services');
        const data = await response.json();
        if (data.success) {
          this.services = data.data;
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    async refreshNodes() {
      try {
        const response = await fetch('/api/swarm/nodes');
        const data = await response.json();
        if (data.success) {
          this.nodes = data.data;
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      }
    },
    async refreshHealth() {
      try {
        const response = await fetch('/api/swarm/health');
        const data = await response.json();
        if (data.success) {
          this.health = data.data;
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      }
    },
    async refreshStatistics() {
      try {
        const response = await fetch('/api/swarm/statistics');
        const data = await response.json();
        if (data.success) {
          this.statistics = data.data;
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      }
    },
    showScaleModal(service) {
      this.selectedService = service;
      this.replicasInput = service.replicas;
      $('#scaleModal').modal('show');
    },
    async scaleService() {
      if (!this.selectedService) return;
      
      this.loading = true;
      try {
        const response = await fetch(`/api/swarm/services/${this.selectedService.name}/scale`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ replicas: this.replicasInput })
        });
        const data = await response.json();
        if (data.success) {
          this.showToast(`Service scaled to ${this.replicasInput} replicas`, 'success');
          $('#scaleModal').modal('hide');
          await this.refreshServices();
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    showLogsModal(service) {
      this.selectedService = service;
      this.serviceLogs = ['Loading...'];
      $('#logsModal').modal('show');
      this.fetchServiceLogs(service.name);
    },
    async fetchServiceLogs(serviceName) {
      try {
        const response = await fetch(`/api/swarm/services/${serviceName}/logs?tail=50`);
        const data = await response.json();
        if (data.success) {
          this.serviceLogs = data.logs;
        }
      } catch (error) {
        this.serviceLogs = [error.message];
      }
    },
    async removeService(serviceName) {
      if (!confirm(`Remove service "${serviceName}"?`)) return;
      
      this.loading = true;
      try {
        const response = await fetch(`/api/swarm/services/${serviceName}`, {
          method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
          this.showToast('Service removed', 'success');
          await this.refreshServices();
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    async drainNode(nodeId) {
      if (!confirm('Drain node? (Tasks will be moved to other nodes)')) return;
      
      this.loading = true;
      try {
        const response = await fetch(`/api/swarm/nodes/${nodeId}/availability`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ availability: 'drain' })
        });
        const data = await response.json();
        if (data.success) {
          this.showToast('Node drained', 'success');
          await this.refreshNodes();
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    async restoreNode(nodeId) {
      this.loading = true;
      try {
        const response = await fetch(`/api/swarm/nodes/${nodeId}/availability`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ availability: 'active' })
        });
        const data = await response.json();
        if (data.success) {
          this.showToast('Node restored', 'success');
          await this.refreshNodes();
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    async removeNode(nodeId) {
      if (!confirm('Remove node from swarm?')) return;
      
      this.loading = true;
      try {
        const response = await fetch(`/api/swarm/nodes/${nodeId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force: false })
        });
        const data = await response.json();
        if (data.success) {
          this.showToast('Node removed', 'success');
          await this.refreshNodes();
        } else {
          this.showToast(data.error, 'error');
        }
      } catch (error) {
        this.showToast(error.message, 'error');
      } finally {
        this.loading = false;
      }
    },
    showToast(message, type = 'info') {
      const id = Math.random();
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 5000);
    }
  }
}
</script>

<style scoped>
.swarm-management {
  padding: 20px;
}

.swarm-header h1 {
  color: #333;
  font-weight: 600;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #007bff;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.stat-card.status-healthy .stat-value {
  color: #28a745;
}

.stat-card.status-unhealthy .stat-value {
  color: #dc3545;
}

.card {
  border: none;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.table {
  font-size: 14px;
}

.badge {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-group-sm .btn {
  padding: 4px 8px;
}

.logs-container {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.logs-container pre {
  color: #333;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
}

.toast {
  background: white;
  padding: 15px 20px;
  margin-bottom: 10px;
  border-radius: 4px;
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
  border-left: 4px solid #007bff;
}

.toast-success {
  border-left-color: #28a745;
  color: #28a745;
}

.toast-error {
  border-left-color: #dc3545;
  color: #dc3545;
}

.nav-tabs .nav-link {
  color: #666;
  border-bottom: 2px solid transparent;
}

.nav-tabs .nav-link.active {
  color: #007bff;
  border-bottom-color: #007bff;
  background: none;
}

.modal-header {
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}
</style>
