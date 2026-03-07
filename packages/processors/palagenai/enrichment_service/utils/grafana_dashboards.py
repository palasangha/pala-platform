"""
Grafana Dashboard Definitions - Dashboard JSON for Prometheus data visualization

Generated dashboard configurations for monitoring enrichment pipeline
"""

import json
from typing import Dict, Any


def get_enrichment_overview_dashboard() -> Dict[str, Any]:
    """Get main overview dashboard"""
    return {
        "dashboard": {
            "title": "Enrichment Pipeline Overview",
            "description": "Real-time monitoring of MCP enrichment pipeline",
            "tags": ["enrichment", "ocr", "mcp"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Documents Enriched (24h)",
                    "targets": [
                        {
                            "expr": 'increase(enrichment_documents_total{status="success"}[24h])',
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                },
                {
                    "title": "Average Completeness Score",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, enrichment_completeness_score)",
                            "refId": "A"
                        }
                    ],
                    "type": "gauge",
                    "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "min": 0,
                            "max": 1,
                            "unit": "percentunit"
                        }
                    }
                },
                {
                    "title": "Daily Budget Status",
                    "targets": [
                        {
                            "expr": "enrichment_budget_percentage_used",
                            "refId": "A"
                        }
                    ],
                    "type": "gauge",
                    "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "min": 0,
                            "max": 100,
                            "unit": "percent",
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 50},
                                    {"color": "red", "value": 80}
                                ]
                            }
                        }
                    }
                },
                {
                    "title": "Documents Pending Review",
                    "targets": [
                        {
                            "expr": "enrichment_review_queue_size",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                },
                {
                    "title": "Completeness Distribution (24h)",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, enrichment_completeness_score)",
                            "refId": "p95"
                        },
                        {
                            "expr": "histogram_quantile(0.50, enrichment_completeness_score)",
                            "refId": "p50"
                        },
                        {
                            "expr": "histogram_quantile(0.05, enrichment_completeness_score)",
                            "refId": "p05"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "title": "Cost by Model (24h)",
                    "targets": [
                        {
                            "expr": "increase(enrichment_claude_cost_usd_total[24h])",
                            "refId": "A",
                            "legendFormat": "{{ model }}"
                        }
                    ],
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ]
        }
    }


def get_agent_performance_dashboard() -> Dict[str, Any]:
    """Get agent performance and health dashboard"""
    return {
        "dashboard": {
            "title": "Agent Performance & Health",
            "description": "MCP agent performance metrics and availability",
            "tags": ["agents", "mcp", "performance"],
            "panels": [
                {
                    "title": "Agent Availability",
                    "targets": [
                        {
                            "expr": "enrichment_agent_available",
                            "refId": "A",
                            "legendFormat": "{{ agent_id }}"
                        }
                    ],
                    "type": "table",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "title": "Agent Response Times (95th percentile)",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, enrichment_agent_response_seconds)",
                            "refId": "A",
                            "legendFormat": "{{ agent_id }}: {{ tool_name }}"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "title": "Agent Errors (24h)",
                    "targets": [
                        {
                            "expr": 'increase(enrichment_agent_errors_total[24h])',
                            "refId": "A",
                            "legendFormat": "{{ agent_id }}: {{ error_type }}"
                        }
                    ],
                    "type": "barchart",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "title": "MCP Request Success Rate",
                    "targets": [
                        {
                            "expr": 'increase(enrichment_mcp_requests_total{status="success"}[1h]) / increase(enrichment_mcp_requests_total[1h])',
                            "refId": "A"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "fieldConfig": {
                        "defaults": {"unit": "percentunit"}
                    }
                }
            ]
        }
    }


def get_cost_tracking_dashboard() -> Dict[str, Any]:
    """Get cost tracking and budget monitoring dashboard"""
    return {
        "dashboard": {
            "title": "Cost Tracking & Budget",
            "description": "Claude API costs and budget monitoring",
            "tags": ["costs", "budget", "claude"],
            "panels": [
                {
                    "title": "Daily Spend ($)",
                    "targets": [
                        {
                            "expr": "enrichment_daily_spend_usd",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    "fieldConfig": {
                        "defaults": {"unit": "currencyUSD"}
                    }
                },
                {
                    "title": "Budget Remaining ($)",
                    "targets": [
                        {
                            "expr": "enrichment_budget_remaining_usd",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                    "fieldConfig": {
                        "defaults": {"unit": "currencyUSD"}
                    }
                },
                {
                    "title": "Budget Usage %",
                    "targets": [
                        {
                            "expr": "enrichment_budget_percentage_used",
                            "refId": "A"
                        }
                    ],
                    "type": "gauge",
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 70},
                                    {"color": "red", "value": 90}
                                ]
                            }
                        }
                    }
                },
                {
                    "title": "Cost per Document ($)",
                    "targets": [
                        {
                            "expr": "increase(enrichment_claude_cost_usd_total[24h]) / increase(enrichment_documents_total{status=\"success\"}[24h])",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                    "fieldConfig": {
                        "defaults": {"unit": "currencyUSD"}
                    }
                },
                {
                    "title": "Cumulative Cost (30d)",
                    "targets": [
                        {
                            "expr": "increase(enrichment_claude_cost_usd_total[30d])",
                            "refId": "A",
                            "legendFormat": "{{ model }}"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4}
                },
                {
                    "title": "Tokens Used (30d)",
                    "targets": [
                        {
                            "expr": "increase(enrichment_api_tokens_total[30d])",
                            "refId": "A",
                            "legendFormat": "{{ model }}-{{ direction }}"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4}
                }
            ]
        }
    }


def get_quality_dashboard() -> Dict[str, Any]:
    """Get document quality and completeness dashboard"""
    return {
        "dashboard": {
            "title": "Document Quality & Completeness",
            "description": "Quality metrics, completeness scores, and missing fields",
            "tags": ["quality", "completeness"],
            "panels": [
                {
                    "title": "Success vs Review vs Error Rate (24h)",
                    "targets": [
                        {
                            "expr": 'increase(enrichment_documents_total[24h])',
                            "refId": "A",
                            "legendFormat": "{{ status }}"
                        }
                    ],
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0}
                },
                {
                    "title": "Completeness Score Distribution",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.99, enrichment_completeness_score)",
                            "refId": "p99"
                        },
                        {
                            "expr": "histogram_quantile(0.95, enrichment_completeness_score)",
                            "refId": "p95"
                        },
                        {
                            "expr": "histogram_quantile(0.50, enrichment_completeness_score)",
                            "refId": "median"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0}
                },
                {
                    "title": "Missing Fields Distribution",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, enrichment_missing_fields)",
                            "refId": "p95"
                        },
                        {
                            "expr": "histogram_quantile(0.50, enrichment_missing_fields)",
                            "refId": "median"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0}
                },
                {
                    "title": "Review Queue Size Over Time",
                    "targets": [
                        {
                            "expr": "enrichment_review_queue_size",
                            "refId": "A"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
                },
                {
                    "title": "OCR Confidence Distribution",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, enrichment_ocr_confidence)",
                            "refId": "p95"
                        },
                        {
                            "expr": "histogram_quantile(0.50, enrichment_ocr_confidence)",
                            "refId": "median"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
                }
            ]
        }
    }


def get_throughput_dashboard() -> Dict[str, Any]:
    """Get processing throughput and performance dashboard"""
    return {
        "dashboard": {
            "title": "Processing Throughput",
            "description": "Processing speed and throughput metrics",
            "tags": ["throughput", "performance"],
            "panels": [
                {
                    "title": "Throughput (docs/hour)",
                    "targets": [
                        {
                            "expr": "enrichment_throughput_docs_per_hour",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0}
                },
                {
                    "title": "Queue Size",
                    "targets": [
                        {
                            "expr": "enrichment_processing_queue_size",
                            "refId": "A"
                        }
                    ],
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0}
                },
                {
                    "title": "Processing Time by Phase (median)",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, enrichment_duration_seconds)",
                            "refId": "A",
                            "legendFormat": "Phase {{ phase }}"
                        }
                    ],
                    "type": "barchart",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4}
                },
                {
                    "title": "Total Enrichment Time Distribution",
                    "targets": [
                        {
                            "expr": 'histogram_quantile(0.99, enrichment_duration_seconds{phase="total"})',
                            "refId": "p99"
                        },
                        {
                            "expr": 'histogram_quantile(0.95, enrichment_duration_seconds{phase="total"})',
                            "refId": "p95"
                        },
                        {
                            "expr": 'histogram_quantile(0.50, enrichment_duration_seconds{phase="total"})',
                            "refId": "median"
                        }
                    ],
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4}
                }
            ]
        }
    }


# Export all dashboards
DASHBOARDS = {
    'enrichment-overview': get_enrichment_overview_dashboard,
    'agent-performance': get_agent_performance_dashboard,
    'cost-tracking': get_cost_tracking_dashboard,
    'document-quality': get_quality_dashboard,
    'throughput': get_throughput_dashboard
}


def get_all_dashboards():
    """Get all dashboard definitions"""
    return {name: func() for name, func in DASHBOARDS.items()}


def export_dashboard_json(dashboard_name: str, output_path: str):
    """
    Export dashboard definition to JSON file

    Args:
        dashboard_name: Dashboard key from DASHBOARDS
        output_path: Path to write JSON file
    """
    if dashboard_name not in DASHBOARDS:
        raise ValueError(f"Unknown dashboard: {dashboard_name}")

    dashboard = DASHBOARDS[dashboard_name]()

    with open(output_path, 'w') as f:
        json.dump(dashboard, f, indent=2)

    print(f"Exported {dashboard_name} to {output_path}")
