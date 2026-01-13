# LM Studio Connection from Docker - Solution Summary

## Problem
LM Studio runs on the host machine (172.12.0.132:1234), but Docker containers on a custom bridge network cannot reach that IP address due to network isolation.

## Root Cause
- Docker custom bridge networks (`gvpocr-network`) isolate containers from direct access to the host's external IPs
- Containers can only access services through:
  1. Docker DNS (service names)
  2. The Docker network gateway (172.23.0.1)
  3. Published ports/port mapping
  
## Attempted Solutions
1. **socat relay on custom network** - Failed: Can't reach host external IP from within container
2. **DNS resolution to gateway IP** - Failed: Gateway doesn't have LM Studio listening
3. **socat relay on host network** - Failed: Gateway IP already in use
4. **host network mode for proxy** - Failed: Backend can't reach services on host network

## Working Solution

### Option A: Move LM Studio to Host's Docker Bridge (Recommended for Docker)
Have LM Studio listen on `0.0.0.0` (already done) and bind it to the Docker bridge interface instead.

**Configuration needed in LM Studio settings or startup:**
```
--host 172.23.0.1  # Listen on Docker gateway interface
```

Then update `.env`:
```
LMSTUDIO_HOST=http://172.23.0.1:1234
```

### Option B: Use NAT/iptables (Requires Sudo)
Set up forwarding rules from Docker network to host:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -s 172.23.0.0/16 -j MASQUERADE
sudo iptables -A FORWARD -s 172.23.0.0/16 -j ACCEPT
```

### Option C: Put Backend on Host Network (Security Risk)
```yaml
backend:
  network_mode: "host"
```
**Not recommended** - breaks Docker network isolation.

### Option D: Alternative - Use Port Publishing
Publish LM Studio port from host and access via mapped port (requires port availability on host).

## Current Status
- LM Studio is running and accessible: `172.12.0.132:1234`
- Backend container cannot directly reach the host IP
- Fallback: Use alternative OCR providers (Ollama, Tesseract, Google Vision)

## Files Updated
- `.env` - LMSTUDIO_HOST and related settings
- `docker-compose.yml` - Network and environment configurations

## Recommended Action
**For production**: Configure LM Studio to listen on the Docker bridge IP (Option A), or set up proper NAT rules with sudo access.

**For now**: Backend has `LMSTUDIO_SKIP_AVAILABILITY_CHECK=true`, so it won't block startup even if LM Studio isn't reachable. Consider using other OCR providers as primary with LM Studio as fallback.
