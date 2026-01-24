"""
Phase 6: Production Deployment - Monitoring Setup
=================================================

This module provides monitoring and observability setup for the ICR system.

Features:
- Prometheus metrics
- Grafana dashboards
- Log aggregation
- Alerting rules
- Health monitoring

Author: ICR Integration Team
Date: 2026-01-23
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringSetup:
    """
    Monitoring and observability setup for ICR system.
    
    Configures Prometheus, Grafana, and logging stack.
    """
    
    def __init__(self):
        """Initialize monitoring setup."""
        logger.info("=" * 80)
        logger.info("Initializing Monitoring Setup")
        logger.info("=" * 80)
        
        self.monitoring_dir = Path(__file__).parent.parent / "deployment" / "monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✓ Monitoring setup initialized")
        logger.info(f"  Directory: {self.monitoring_dir}")
        logger.info("=" * 80)
    
    def generate_prometheus_config(self) -> Dict[str, Any]:
        """Generate Prometheus configuration."""
        return {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s",
                "external_labels": {
                    "cluster": "icr-production",
                    "replica": "1"
                }
            },
            "alerting": {
                "alertmanagers": [{
                    "static_configs": [{
                        "targets": ["alertmanager:9093"]
                    }]
                }]
            },
            "rule_files": [
                "alerts.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": "prometheus",
                    "static_configs": [{
                        "targets": ["localhost:9090"]
                    }]
                },
                {
                    "job_name": "icr-backend",
                    "kubernetes_sd_configs": [{
                        "role": "pod",
                        "namespaces": {"names": ["icr-system"]}
                    }],
                    "relabel_configs": [{
                        "source_labels": ["__meta_kubernetes_pod_label_component"],
                        "action": "keep",
                        "regex": "backend"
                    }]
                },
                {
                    "job_name": "icr-worker",
                    "kubernetes_sd_configs": [{
                        "role": "pod",
                        "namespaces": {"names": ["icr-system"]}
                    }],
                    "relabel_configs": [{
                        "source_labels": ["__meta_kubernetes_pod_label_component"],
                        "action": "keep",
                        "regex": "worker"
                    }]
                },
                {
                    "job_name": "kubernetes-nodes",
                    "kubernetes_sd_configs": [{
                        "role": "node"
                    }]
                },
                {
                    "job_name": "kubernetes-pods",
                    "kubernetes_sd_configs": [{
                        "role": "pod"
                    }]
                }
            ]
        }
    
    def generate_alert_rules(self) -> Dict[str, Any]:
        """Generate Prometheus alert rules."""
        return {
            "groups": [
                {
                    "name": "icr_alerts",
                    "interval": "30s",
                    "rules": [
                        {
                            "alert": "HighErrorRate",
                            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05",
                            "for": "5m",
                            "labels": {"severity": "critical"},
                            "annotations": {
                                "summary": "High error rate detected",
                                "description": "Error rate is {{ $value }} errors/sec"
                            }
                        },
                        {
                            "alert": "HighLatency",
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2",
                            "for": "10m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High latency detected",
                                "description": "95th percentile latency is {{ $value }}s"
                            }
                        },
                        {
                            "alert": "HighMemoryUsage",
                            "expr": "container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9",
                            "for": "5m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High memory usage",
                                "description": "Memory usage is {{ $value | humanizePercentage }}"
                            }
                        },
                        {
                            "alert": "PodCrashLooping",
                            "expr": "rate(kube_pod_container_status_restarts_total[15m]) > 0",
                            "for": "5m",
                            "labels": {"severity": "critical"},
                            "annotations": {
                                "summary": "Pod is crash looping",
                                "description": "Pod {{ $labels.pod }} is restarting"
                            }
                        },
                        {
                            "alert": "LowDiskSpace",
                            "expr": "node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1",
                            "for": "5m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "Low disk space",
                                "description": "Disk usage is {{ $value | humanizePercentage }}"
                            }
                        }
                    ]
                }
            ]
        }
    
    def generate_grafana_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana dashboard configuration."""
        return {
            "dashboard": {
                "title": "ICR System Overview",
                "tags": ["icr", "production"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Request Rate",
                        "type": "graph",
                        "targets": [{
                            "expr": "rate(http_requests_total[5m])",
                            "legendFormat": "{{method}} {{path}}"
                        }],
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8}
                    },
                    {
                        "id": 2,
                        "title": "Error Rate",
                        "type": "graph",
                        "targets": [{
                            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
                            "legendFormat": "Errors"
                        }],
                        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
                    },
                    {
                        "id": 3,
                        "title": "Response Time (p95)",
                        "type": "graph",
                        "targets": [{
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                            "legendFormat": "p95"
                        }],
                        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
                    },
                    {
                        "id": 4,
                        "title": "Active Pods",
                        "type": "stat",
                        "targets": [{
                            "expr": "count(kube_pod_status_phase{namespace=\"icr-system\", phase=\"Running\"})"
                        }],
                        "gridPos": {"x": 12, "y": 8, "w": 6, "h": 4}
                    },
                    {
                        "id": 5,
                        "title": "CPU Usage",
                        "type": "graph",
                        "targets": [{
                            "expr": "rate(container_cpu_usage_seconds_total[5m])",
                            "legendFormat": "{{pod}}"
                        }],
                        "gridPos": {"x": 0, "y": 16, "w": 12, "h": 8}
                    },
                    {
                        "id": 6,
                        "title": "Memory Usage",
                        "type": "graph",
                        "targets": [{
                            "expr": "container_memory_usage_bytes",
                            "legendFormat": "{{pod}}"
                        }],
                        "gridPos": {"x": 12, "y": 16, "w": 12, "h": 8}
                    }
                ]
            }
        }
    
    def generate_logging_config(self) -> Dict[str, Any]:
        """Generate logging stack configuration (Loki/Fluentd)."""
        return {
            "loki": {
                "auth_enabled": False,
                "server": {
                    "http_listen_port": 3100
                },
                "ingester": {
                    "lifecycler": {
                        "ring": {
                            "kvstore": {
                                "store": "inmemory"
                            }
                        }
                    },
                    "chunk_idle_period": "5m",
                    "chunk_retain_period": "30s"
                },
                "schema_config": {
                    "configs": [{
                        "from": "2020-01-01",
                        "store": "boltdb",
                        "object_store": "filesystem",
                        "schema": "v11",
                        "index": {
                            "prefix": "index_",
                            "period": "168h"
                        }
                    }]
                },
                "storage_config": {
                    "boltdb": {
                        "directory": "/tmp/loki/index"
                    },
                    "filesystem": {
                        "directory": "/tmp/loki/chunks"
                    }
                }
            },
            "promtail": {
                "server": {
                    "http_listen_port": 9080
                },
                "clients": [{
                    "url": "http://loki:3100/loki/api/v1/push"
                }],
                "scrape_configs": [{
                    "job_name": "kubernetes-pods",
                    "kubernetes_sd_configs": [{
                        "role": "pod"
                    }],
                    "relabel_configs": [
                        {
                            "source_labels": ["__meta_kubernetes_pod_label_app"],
                            "target_label": "app"
                        },
                        {
                            "source_labels": ["__meta_kubernetes_pod_label_component"],
                            "target_label": "component"
                        }
                    ]
                }]
            }
        }
    
    def setup_monitoring(self) -> Dict[str, Any]:
        """
        Setup complete monitoring stack.
        
        Returns:
            Setup result
        """
        logger.info("=" * 80)
        logger.info("Setting Up Monitoring Stack")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Generate configurations
        prometheus_config = self.generate_prometheus_config()
        alert_rules = self.generate_alert_rules()
        grafana_dashboard = self.generate_grafana_dashboard()
        logging_config = self.generate_logging_config()
        
        # Save configurations
        configs_saved = []
        
        # Prometheus
        prom_file = self.monitoring_dir / "prometheus.yml"
        import yaml
        with open(prom_file, 'w') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False)
        logger.info(f"✓ Saved: {prom_file}")
        configs_saved.append(str(prom_file))
        
        # Alert rules
        alerts_file = self.monitoring_dir / "alerts.yml"
        with open(alerts_file, 'w') as f:
            yaml.dump(alert_rules, f, default_flow_style=False)
        logger.info(f"✓ Saved: {alerts_file}")
        configs_saved.append(str(alerts_file))
        
        # Grafana dashboard
        grafana_file = self.monitoring_dir / "grafana-dashboard.json"
        with open(grafana_file, 'w') as f:
            json.dump(grafana_dashboard, f, indent=2)
        logger.info(f"✓ Saved: {grafana_file}")
        configs_saved.append(str(grafana_file))
        
        # Logging config
        logging_file = self.monitoring_dir / "logging-config.yml"
        with open(logging_file, 'w') as f:
            yaml.dump(logging_config, f, default_flow_style=False)
        logger.info(f"✓ Saved: {logging_file}")
        configs_saved.append(str(logging_file))
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "configs_saved": configs_saved,
            "duration": duration,
            "components": ["prometheus", "grafana", "loki", "promtail"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("=" * 80)
        logger.info("✓ Monitoring stack configured")
        logger.info("=" * 80)
        logger.info(f"  Components: {len(result['components'])}")
        logger.info(f"  Configs saved: {len(configs_saved)}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info("=" * 80)
        
        return result


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("ICR Monitoring Setup - Phase 6")
    print("=" * 80 + "\n")
    
    setup = MonitoringSetup()
    
    print("\n📊 Setting up monitoring stack...\n")
    result = setup.setup_monitoring()
    
    print("\n" + "=" * 80)
    print("✓ Monitoring setup complete!")
    print("=" * 80)
    print(f"\nConfigurations saved:")
    for config in result["configs_saved"]:
        print(f"  - {config}")
    print()


if __name__ == "__main__":
    main()
