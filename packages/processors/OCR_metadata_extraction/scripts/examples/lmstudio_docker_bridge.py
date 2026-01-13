#!/usr/bin/env python3
"""
LMStudio Docker Bridge
Runs on the host and forwards connections from Docker containers to LMStudio
"""

import socket
import threading
import sys
import subprocess
import os
import signal
import time

HOST_IP = "172.12.0.132"  # Where LMStudio actually listens (host external IP)
HOST_PORT = 1234  # LMStudio port
DOCKER_GATEWAY_IP = "172.23.0.1"  # Docker network gateway
DOCKER_LISTEN_PORT = 1234  # Port to listen on for Docker containers

def forward_data(src, dst, direction):
    """Forward data between two sockets"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        pass
    finally:
        try:
            src.close()
            dst.close()
        except:
            pass

def handle_client(client_socket, addr):
    """Handle incoming connection from Docker container"""
    try:
        # Connect to LMStudio on the host IP
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((HOST_IP, HOST_PORT))

        print(f"[{addr[0]}:{addr[1]}] Connected to LMStudio on {HOST_IP}:{HOST_PORT}")

        # Forward data bidirectionally
        t1 = threading.Thread(target=forward_data, args=(client_socket, server_socket, "client->server"))
        t2 = threading.Thread(target=forward_data, args=(server_socket, client_socket, "server->client"))

        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()

    except Exception as e:
        print(f"[{addr[0]}:{addr[1]}] Error: {e}")
        try:
            client_socket.close()
        except:
            pass

def kill_process_on_port(ip, port):
    """Kill any existing process listening on the given IP:port"""
    try:
        # Try to find process using the port with netstat
        result = subprocess.run(
            f"netstat -tlnp 2>/dev/null | grep {ip}:{port}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.stdout.strip():
            # Parse netstat output to get PID
            # Format: tcp 0 0 172.23.0.1:1234 0.0.0.0:* LISTEN 12345/python3
            try:
                parts = result.stdout.strip().split()
                pid_info = parts[-1]  # Get the PID/program part
                pid = int(pid_info.split('/')[0])

                print(f"⚠ Found existing process on {ip}:{port} (PID: {pid})")
                print(f"  Killing process {pid}...")

                os.kill(pid, signal.SIGTERM)
                time.sleep(1)

                # Verify it's dead
                try:
                    os.kill(pid, 0)
                    # Still alive, force kill
                    os.kill(pid, signal.SIGKILL)
                    print(f"  Force killed process {pid}")
                except ProcessLookupError:
                    print(f"  ✓ Process {pid} terminated successfully")

                time.sleep(1)
                return True
            except (ValueError, IndexError) as e:
                print(f"⚠ Could not parse netstat output: {e}")
                return False

        return False

    except subprocess.TimeoutExpired:
        print("⚠ Timeout checking for existing process")
        return False
    except Exception as e:
        print(f"⚠ Error checking for existing process: {e}")
        return False

def main():
    """Start the Docker bridge server"""
    print("=" * 60)
    print("LMStudio Docker Bridge")
    print("=" * 60)
    print(f"Listening on: {DOCKER_GATEWAY_IP}:{DOCKER_LISTEN_PORT}")
    print(f"Forwarding to: {HOST_IP}:{HOST_PORT}")
    print(f"Docker containers can connect to: http://{DOCKER_GATEWAY_IP}:{DOCKER_LISTEN_PORT}")
    print("=" * 60)
    print()

    # Check if port is already in use and kill any existing process
    print("Checking for existing process on the port...")
    if kill_process_on_port(DOCKER_GATEWAY_IP, DOCKER_LISTEN_PORT):
        print()

    # Create and bind socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((DOCKER_GATEWAY_IP, DOCKER_LISTEN_PORT))
        server_socket.listen(10)
        print(f"✓ Server started successfully")
        print()

        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"[{addr[0]}:{addr[1]}] Incoming connection from Docker")

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()

            except KeyboardInterrupt:
                print("\n✓ Shutting down...")
                break
            except Exception as e:
                print(f"Error accepting connection: {e}")

    except OSError as e:
        print(f"✗ Error: {e}")
        print()
        print("Possible solutions:")
        print(f"1. LMStudio is not running on {HOST_IP}:{HOST_PORT}")
        print("2. The Docker gateway IP (172.23.0.1) is already in use")
        print("3. Permission issue - try running with: sudo python3 lmstudio_docker_bridge.py")
        sys.exit(1)
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
