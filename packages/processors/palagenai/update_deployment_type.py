#!/usr/bin/env python3
"""
Update existing deployments to include deployment_type field
"""
import sys
sys.path.insert(0, '/app')

from pymongo import MongoClient
import os

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp%40123@mongodb:27017/gvpocr?authSource=admin')
client = MongoClient(mongo_uri)
db = client.gvpocr

# Update all deployments without deployment_type
result = db.worker_deployments.update_many(
    {'deployment_type': {'$exists': False}},
    {
        '$set': {
            'deployment_type': 'docker_socket',
            'use_docker_socket': True,
            'docker_socket_port': 2375,
            'docker_tls': False,
            'docker_verify_tls': False
        }
    }
)

print(f"Updated {result.modified_count} deployment(s)")

# Show all deployments
deployments = list(db.worker_deployments.find())
print(f"\nTotal deployments: {len(deployments)}")
for dep in deployments:
    print(f"\nDeployment: {dep['worker_name']}")
    print(f"  ID: {dep['_id']}")
    print(f"  Host: {dep['host']}")
    print(f"  Deployment Type: {dep.get('deployment_type', 'NOT SET')}")
    print(f"  Docker Socket Port: {dep.get('docker_socket_port', 'NOT SET')}")
    print(f"  Status: {dep['status']}")
