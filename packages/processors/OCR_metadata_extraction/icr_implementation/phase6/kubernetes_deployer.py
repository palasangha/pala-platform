"""
Phase 6: Production Deployment - Kubernetes Deployer
====================================================

This module provides Kubernetes deployment automation for the ICR system.

Features:
- K8s manifest generation
- Deployment orchestration
- Service configuration
- Ingress setup
- ConfigMap/Secret management
- Health check configuration

Author: ICR Integration Team
Date: 2026-01-23
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KubernetesDeployer:
    """
    Kubernetes deployment manager for ICR system.
    
    Generates and manages K8s manifests for all components.
    """
    
    def __init__(self, namespace: str = "icr-system"):
        """
        Initialize Kubernetes deployer.
        
        Args:
            namespace: Kubernetes namespace
        """
        logger.info("=" * 80)
        logger.info("Initializing Kubernetes Deployer")
        logger.info("=" * 80)
        
        self.namespace = namespace
        self.manifests_dir = Path(__file__).parent.parent / "deployment" / "k8s"
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        
        # Deployment configuration
        self.config = {
            "backend": {
                "replicas": 3,
                "port": 8000,
                "resources": {
                    "requests": {"cpu": "500m", "memory": "1Gi"},
                    "limits": {"cpu": "2000m", "memory": "4Gi"}
                }
            },
            "frontend": {
                "replicas": 2,
                "port": 80,
                "resources": {
                    "requests": {"cpu": "100m", "memory": "128Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"}
                }
            },
            "worker": {
                "replicas": 5,
                "resources": {
                    "requests": {"cpu": "1000m", "memory": "2Gi"},
                    "limits": {"cpu": "4000m", "memory": "8Gi"}
                }
            }
        }
        
        logger.info(f"✓ Kubernetes Deployer initialized")
        logger.info(f"  Namespace: {self.namespace}")
        logger.info(f"  Manifests directory: {self.manifests_dir}")
        logger.info(f"  Components: {len(self.config)}")
        logger.info("=" * 80)
    
    def generate_namespace(self) -> Dict[str, Any]:
        """Generate namespace manifest."""
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": self.namespace,
                "labels": {
                    "app": "icr",
                    "environment": "production"
                }
            }
        }
    
    def generate_deployment(self, component: str) -> Dict[str, Any]:
        """
        Generate deployment manifest for component.
        
        Args:
            component: Component name
            
        Returns:
            Deployment manifest
        """
        config = self.config[component]
        
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"icr-{component}",
                "namespace": self.namespace,
                "labels": {
                    "app": "icr",
                    "component": component
                }
            },
            "spec": {
                "replicas": config["replicas"],
                "selector": {
                    "matchLabels": {
                        "app": "icr",
                        "component": component
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "icr",
                            "component": component
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": component,
                            "image": f"localhost:5000/icr/{component}:1.0.0",
                            "resources": config["resources"],
                            "env": [
                                {"name": "ENVIRONMENT", "value": "production"},
                                {"name": "LOG_LEVEL", "value": "INFO"}
                            ]
                        }]
                    }
                }
            }
        }
        
        # Add port for backend/frontend
        if "port" in config:
            manifest["spec"]["template"]["spec"]["containers"][0]["ports"] = [{
                "containerPort": config["port"],
                "name": "http"
            }]
            
            # Add health checks
            manifest["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = {
                "httpGet": {
                    "path": "/api/health" if component == "backend" else "/",
                    "port": config["port"]
                },
                "initialDelaySeconds": 30,
                "periodSeconds": 10
            }
            
            manifest["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
                "httpGet": {
                    "path": "/api/health" if component == "backend" else "/",
                    "port": config["port"]
                },
                "initialDelaySeconds": 10,
                "periodSeconds": 5
            }
        
        return manifest
    
    def generate_service(self, component: str) -> Optional[Dict[str, Any]]:
        """
        Generate service manifest for component.
        
        Args:
            component: Component name
            
        Returns:
            Service manifest or None if no service needed
        """
        config = self.config[component]
        
        if "port" not in config:
            return None
        
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"icr-{component}",
                "namespace": self.namespace,
                "labels": {
                    "app": "icr",
                    "component": component
                }
            },
            "spec": {
                "selector": {
                    "app": "icr",
                    "component": component
                },
                "ports": [{
                    "port": config["port"],
                    "targetPort": config["port"],
                    "name": "http"
                }],
                "type": "ClusterIP"
            }
        }
    
    def generate_ingress(self) -> Dict[str, Any]:
        """Generate ingress manifest for external access."""
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": "icr-ingress",
                "namespace": self.namespace,
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            },
            "spec": {
                "ingressClassName": "nginx",
                "tls": [{
                    "hosts": ["icr.example.com"],
                    "secretName": "icr-tls"
                }],
                "rules": [{
                    "host": "icr.example.com",
                    "http": {
                        "paths": [
                            {
                                "path": "/api",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": "icr-backend",
                                        "port": {"number": 8000}
                                    }
                                }
                            },
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": "icr-frontend",
                                        "port": {"number": 80}
                                    }
                                }
                            }
                        ]
                    }
                }]
            }
        }
    
    def generate_configmap(self) -> Dict[str, Any]:
        """Generate ConfigMap for application configuration."""
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "icr-config",
                "namespace": self.namespace
            },
            "data": {
                "OCR_PROVIDER": "paddleocr",
                "VLM_PROVIDER": "openai",
                "LLM_PROVIDER": "openai",
                "VECTOR_STORE": "chromadb",
                "MAX_WORKERS": "5",
                "LOG_LEVEL": "INFO"
            }
        }
    
    def generate_hpa(self, component: str) -> Dict[str, Any]:
        """
        Generate HorizontalPodAutoscaler for component.
        
        Args:
            component: Component name
            
        Returns:
            HPA manifest
        """
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"icr-{component}-hpa",
                "namespace": self.namespace
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": f"icr-{component}"
                },
                "minReplicas": self.config[component]["replicas"],
                "maxReplicas": self.config[component]["replicas"] * 3,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": 70
                            }
                        }
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": 80
                            }
                        }
                    }
                ]
            }
        }
    
    def save_manifest(self, manifest: Dict[str, Any], filename: str):
        """
        Save manifest to YAML file.
        
        Args:
            manifest: Manifest dictionary
            filename: Output filename
        """
        filepath = self.manifests_dir / filename
        with open(filepath, 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✓ Manifest saved: {filepath}")
    
    def generate_all_manifests(self) -> List[str]:
        """
        Generate all Kubernetes manifests.
        
        Returns:
            List of generated manifest files
        """
        logger.info("=" * 80)
        logger.info("Generating Kubernetes Manifests")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        manifests = []
        
        # Namespace
        self.save_manifest(self.generate_namespace(), "00-namespace.yaml")
        manifests.append("00-namespace.yaml")
        
        # ConfigMap
        self.save_manifest(self.generate_configmap(), "01-configmap.yaml")
        manifests.append("01-configmap.yaml")
        
        # Deployments and Services
        for i, component in enumerate(self.config.keys(), start=2):
            # Deployment
            deployment = self.generate_deployment(component)
            filename = f"{i:02d}-{component}-deployment.yaml"
            self.save_manifest(deployment, filename)
            manifests.append(filename)
            
            # Service
            service = self.generate_service(component)
            if service:
                filename = f"{i:02d}-{component}-service.yaml"
                self.save_manifest(service, filename)
                manifests.append(filename)
            
            # HPA
            hpa = self.generate_hpa(component)
            filename = f"{i:02d}-{component}-hpa.yaml"
            self.save_manifest(hpa, filename)
            manifests.append(filename)
        
        # Ingress
        self.save_manifest(self.generate_ingress(), "99-ingress.yaml")
        manifests.append("99-ingress.yaml")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("✓ All manifests generated")
        logger.info("=" * 80)
        logger.info(f"  Total files: {len(manifests)}")
        logger.info(f"  Directory: {self.manifests_dir}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info("=" * 80)
        
        return manifests
    
    def deploy(self) -> Dict[str, Any]:
        """
        Deploy to Kubernetes cluster.
        
        Returns:
            Deployment result
        """
        logger.info("=" * 80)
        logger.info("Deploying to Kubernetes")
        logger.info("=" * 80)
        
        logger.warning("Mock mode: Simulating Kubernetes deployment")
        
        result = {
            "status": "success",
            "namespace": self.namespace,
            "deployments": list(self.config.keys()),
            "total_pods": sum(c["replicas"] for c in self.config.values()),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("✓ Deployment successful (Mock)")
        logger.info(f"  Namespace: {self.namespace}")
        logger.info(f"  Deployments: {len(result['deployments'])}")
        logger.info(f"  Total pods: {result['total_pods']}")
        logger.info("=" * 80)
        
        return result


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("ICR Kubernetes Deployer - Phase 6")
    print("=" * 80 + "\n")
    
    deployer = KubernetesDeployer()
    
    # Generate manifests
    print("\n📝 Generating Kubernetes manifests...\n")
    manifests = deployer.generate_all_manifests()
    
    # Deploy
    print("\n🚀 Deploying to Kubernetes...\n")
    result = deployer.deploy()
    
    print("\n" + "=" * 80)
    print("✓ Kubernetes deployment complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
