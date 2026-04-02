#!/usr/bin/env python3
"""
Remote Worker Tunnel Manager
-----------------------------
Establishes and maintains all required SSH reverse tunnels to the remote Mac
worker, then verifies the worker container is healthy and consuming from NSQ.

Usage:
    python setup_remote_worker_tunnels.py [--check-only] [--restart-worker]

Options:
    --check-only      Only verify tunnel/worker health, do not create tunnels
    --restart-worker  Force-restart the remote worker container after setup
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────────────

REMOTE_USER = "tod"
REMOTE_HOST = "172.12.0.84"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")

SSH_BASE_OPTS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=10",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-i", SSH_KEY,
]

REMOTE_DOCKER_BIN = "/opt/homebrew/bin/docker"
REMOTE_WORKER_CONTAINER = "gvpocr-remote-worker"
REMOTE_WORKER_DIR = "/Users/tod/ocr-worker"

NSQ_HTTP_PORT = 4151
NSQ_BULK_TOPIC = "bulk_ocr_file_tasks"
NSQ_BULK_CHANNEL = "bulk_ocr_workers"
WORKER_CONNECT_TIMEOUT = 60   # seconds

# All tunnels required for the remote worker.
# Each creates:  -R remote_port:localhost:local_port
# making our service at local_port available as localhost:remote_port on the Mac.
@dataclass
class Tunnel:
    local_port: int
    remote_port: int
    description: str


TUNNELS = [
    Tunnel(4150,  24150, "NSQ TCP"),
    Tunnel(4161,  24161, "NSQ lookupd"),
    Tunnel(5000,  25000, "Backend API"),
    Tunnel(1234,  21234, "LM Studio"),
    Tunnel(11434, 21134, "Ollama"),
    Tunnel(27017, 27017, "MongoDB"),
]


# ── Colours ───────────────────────────────────────────────────────────────────

GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}✓{RESET} {msg}")
def warn(msg): print(f"{YELLOW}!{RESET} {msg}")
def err(msg):  print(f"{RED}✗{RESET} {msg}", file=sys.stderr)
def info(msg): print(f"  {msg}")


# ── SSH helpers ───────────────────────────────────────────────────────────────

def run(cmd: list[str], *, capture: bool = False, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a command, raising CalledProcessError on non-zero exit."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )


def remote(command: str, *, capture: bool = True, timeout: int = 30) -> str:
    """
    Execute a shell command on the remote host via SSH through the backend
    container (port 22 is firewalled from host but reachable from Docker network).
    Returns stdout as a stripped string.
    Raises subprocess.CalledProcessError on non-zero exit.
    """
    result = subprocess.run(
        [
            "docker", "exec", "gvpocr-backend",
            "ssh", *SSH_BASE_OPTS,
            f"{REMOTE_USER}@{REMOTE_HOST}",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def check_ssh_reachable() -> bool:
    """Return True if port 22 on the remote host is open (checked via Docker network)."""
    result = subprocess.run(
        [
            "docker", "exec", "gvpocr-backend",
            "python3", "-c",
            f"import socket; s=socket.socket(); s.settimeout(4);"
            f"r=s.connect_ex(('{REMOTE_HOST}',22)); s.close(); exit(0 if r==0 else 1)",
        ],
        capture_output=True,
        timeout=10,
    )
    return result.returncode == 0


def copy_key_to_container():
    """Make the SSH key available inside the backend container."""
    subprocess.run(
        ["docker", "cp", SSH_KEY, "gvpocr-backend:/tmp/remote_worker_key"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["docker", "exec", "gvpocr-backend", "chmod", "600", "/tmp/remote_worker_key"],
        check=True, capture_output=True,
    )


# ── Tunnel helpers ────────────────────────────────────────────────────────────

def tunnel_running(tunnel: Tunnel) -> bool:
    """Return True if a reverse tunnel process for this port pair is already running."""
    needle = f"-R {tunnel.remote_port}:localhost:{tunnel.local_port}"
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True, text=True,
    )
    return any(
        needle in line and REMOTE_HOST in line
        for line in result.stdout.splitlines()
        if "grep" not in line
    )


def start_tunnel(tunnel: Tunnel):
    """
    Start a reverse SSH tunnel in a background keep-alive loop.
    The loop restarts the tunnel automatically if it drops.
    """
    cmd = (
        f"while true; do "
        f"ssh {' '.join(SSH_BASE_OPTS)} -f -N "
        f"-R {tunnel.remote_port}:localhost:{tunnel.local_port} "
        f"{REMOTE_USER}@{REMOTE_HOST} 2>/dev/null; "
        f"sleep 5; done"
    )
    proc = subprocess.Popen(
        ["bash", "-c", cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    # Give the ssh process a moment to establish
    time.sleep(1.5)
    return proc


# ── NSQ health ────────────────────────────────────────────────────────────────

def nsq_remote_client_count() -> int:
    """
    Query the NSQ HTTP API and return how many clients connected to
    bulk_ocr_workers appear to be from the remote Mac worker
    (identified by hostname containing 'tod' or 'mac').
    """
    try:
        url = f"http://localhost:{NSQ_HTTP_PORT}/stats?format=json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        for topic in data.get("topics", []):
            if topic.get("topic_name") != NSQ_BULK_TOPIC:
                continue
            for ch in topic.get("channels", []):
                if ch.get("channel_name") != NSQ_BULK_CHANNEL:
                    continue
                clients = ch.get("clients", [])
                remote = [
                    c for c in clients
                    if any(k in c.get("hostname", "").lower() for k in ("tod", "mac"))
                ]
                return len(remote)
    except Exception:
        pass
    return 0


def worker_log_shows_connected() -> bool:
    """Check recent container logs for the NSQ connection-successful message."""
    try:
        logs = remote(
            f"export PATH=$PATH:{Path(REMOTE_DOCKER_BIN).parent}; "
            f"docker logs --since 90s {REMOTE_WORKER_CONTAINER} 2>&1",
            timeout=15,
        )
        return "connection successful" in logs
    except Exception:
        return False


# ── Container management ─────────────────────────────────────────────────────

def get_container_status() -> str:
    """Return the Docker container status string, or 'not_found'."""
    try:
        return remote(
            f"export PATH=$PATH:{Path(REMOTE_DOCKER_BIN).parent}; "
            f"docker inspect --format='{{{{.State.Status}}}}' {REMOTE_WORKER_CONTAINER} 2>/dev/null "
            f"|| echo not_found",
            timeout=15,
        )
    except subprocess.CalledProcessError:
        return "not_found"


def start_container():
    remote(
        f"export PATH=$PATH:{Path(REMOTE_DOCKER_BIN).parent}; "
        f"cd {REMOTE_WORKER_DIR} && docker compose up -d",
        timeout=30,
    )


def restart_container():
    remote(
        f"export PATH=$PATH:{Path(REMOTE_DOCKER_BIN).parent}; "
        f"docker restart {REMOTE_WORKER_CONTAINER}",
        timeout=30,
    )


def get_container_logs(lines: int = 20) -> str:
    try:
        return remote(
            f"export PATH=$PATH:{Path(REMOTE_DOCKER_BIN).parent}; "
            f"docker logs --tail {lines} {REMOTE_WORKER_CONTAINER} 2>&1",
            timeout=15,
        )
    except Exception:
        return "(could not retrieve logs)"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-only", action="store_true", help="Only check health, do not create tunnels")
    parser.add_argument("--restart-worker", action="store_true", help="Force-restart the remote worker container")
    args = parser.parse_args()

    print()
    print("════════════════════════════════════════════════════════")
    print("  Remote Worker Tunnel Manager")
    print(f"  Remote: {REMOTE_USER}@{REMOTE_HOST}")
    print("════════════════════════════════════════════════════════")
    print()

    # ── Step 1: SSH connectivity ──────────────────────────────────────────────
    print("Step 1: Checking SSH connectivity...")

    if not check_ssh_reachable():
        err(f"Cannot reach {REMOTE_HOST}:22")
        err("Ensure the remote Mac is online and SSH is running.")
        sys.exit(1)

    try:
        copy_key_to_container()
        remote("echo ok")
    except Exception as exc:
        err(f"SSH login failed: {exc}")
        err("Ensure ~/.ssh/id_rsa is authorized on the remote machine.")
        sys.exit(1)

    ok("SSH connectivity verified")

    # ── Step 2: Tunnels ───────────────────────────────────────────────────────
    print()
    if args.check_only:
        print("Step 2: Checking tunnel status (check-only mode)...")
    else:
        print("Step 2: Setting up SSH tunnels...")

    failed_tunnels = []
    for tunnel in TUNNELS:
        label = f"[{tunnel.description:<12}]  localhost:{tunnel.local_port} → remote:{tunnel.remote_port}"
        if tunnel_running(tunnel):
            ok(f"Already running  {label}")
        elif args.check_only:
            err(f"Not running      {label}")
            failed_tunnels.append(tunnel)
        else:
            warn(f"Starting         {label}")
            try:
                start_tunnel(tunnel)
                if tunnel_running(tunnel):
                    ok(f"Started          {label}")
                else:
                    err(f"Failed to start  {label}")
                    failed_tunnels.append(tunnel)
            except Exception as exc:
                err(f"Error starting tunnel [{tunnel.description}]: {exc}")
                failed_tunnels.append(tunnel)

    if args.check_only and failed_tunnels:
        print()
        err("Some tunnels are not running. Re-run without --check-only to fix.")
        sys.exit(1)

    if failed_tunnels:
        warn(f"{len(failed_tunnels)} tunnel(s) failed to start — worker may have limited connectivity")

    # ── Step 3: Remote worker container ──────────────────────────────────────
    print()
    print("Step 3: Checking remote worker container...")

    need_restart = args.restart_worker
    try:
        status = get_container_status()
        if status == "running":
            ok(f"Container '{REMOTE_WORKER_CONTAINER}' is running")
        elif status == "not_found":
            warn(f"Container '{REMOTE_WORKER_CONTAINER}' not found — starting via docker compose")
            start_container()
            ok("Container started")
            need_restart = False
        else:
            warn(f"Container is '{status}' — will restart")
            need_restart = True
    except subprocess.CalledProcessError as exc:
        err(f"Failed to check container status: {exc.stderr.strip()}")
        sys.exit(1)

    if need_restart:
        info(f"Restarting {REMOTE_WORKER_CONTAINER}...")
        try:
            restart_container()
            ok("Container restarted")
        except subprocess.CalledProcessError as exc:
            err(f"Failed to restart container: {exc.stderr.strip()}")
            sys.exit(1)

    # ── Step 4: Verify worker appears in NSQ ─────────────────────────────────
    print()
    print("Step 4: Verifying worker connects to NSQ...")

    start = time.time()
    connected = False
    while time.time() - start < WORKER_CONNECT_TIMEOUT:
        elapsed = int(time.time() - start)
        count = nsq_remote_client_count()
        if count > 0:
            ok(f"Remote worker connected to NSQ ({count} client(s) on {NSQ_BULK_CHANNEL})")
            connected = True
            break
        info(f"Waiting for worker to connect... ({elapsed}s / {WORKER_CONNECT_TIMEOUT}s)")
        time.sleep(3)

    if not connected:
        # Fallback: check container logs directly
        if worker_log_shows_connected():
            ok("Worker connected to NSQ (confirmed via container logs)")
            connected = True
        else:
            err(f"Worker did not connect to NSQ within {WORKER_CONNECT_TIMEOUT}s")
            print()
            warn("Recent worker logs:")
            for line in get_container_logs(20).splitlines():
                info(line)
            sys.exit(1)

    # ── Done ─────────────────────────────────────────────────────────────────
    print()
    print("════════════════════════════════════════════════════════")
    ok("Remote worker tunnel setup complete")
    print("════════════════════════════════════════════════════════")
    print()


if __name__ == "__main__":
    main()
