#!/usr/bin/env python3
import docker
import time

# Connect to Docker socket on remote machine
client = docker.DockerClient(base_url='tcp://172.12.0.96:2375')

try:
    # List running containers
    print("=== Running Containers ===")
    containers = client.containers.list()
    for container in containers:
        print(f"Container: {container.name} (ID: {container.id[:12]})")
    
    if containers:
        # Get streaming logs from the first container
        container = containers[0]
        print(f"\n=== Streaming logs from {container.name} ===")
        print("Last 50 lines:\n")
        
        logs = container.logs(stream=True, tail=50)
        line_count = 0
        for line in logs:
            print(line.decode('utf-8'), end='')
            line_count += 1
            if line_count >= 50:
                break
        
        print("\n=== Test Complete ===")
    else:
        print("No running containers found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
