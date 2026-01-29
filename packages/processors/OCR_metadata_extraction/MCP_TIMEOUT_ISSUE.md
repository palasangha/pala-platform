# MCP Server Timeout Issue - Root Cause Analysis

## Problem
Enrichment workers timeout after 120-180 seconds waiting for MCP server responses, even though agents process requests in 1-2 seconds.

## Root Cause
**Timeout mismatch** between MCP server and enrichment workers:

- **MCP Server internal timeout**: `30 seconds` (tool-invoker.ts line 38)
- **Enrichment worker timeout**: `120-180 seconds` (for entity/structure agents)
- **Agent actual processing time**: `1-2 seconds` ✅

## What Happens

### Correct Flow:
1. Enrichment worker → MCP server: `tools/invoke` request
2. MCP server → Agent: Forward invocation
3. Agent processes → Returns result (1-2s) ✅
4. MCP server receives response → Resolves promise
5. MCP server → Enrichment worker: Send response ✅

### Actual Broken Flow:
1. Enrichment worker → MCP server: `tools/invoke` request  
2. MCP server → Agent: Forward invocation
3. **MCP ToolInvoker starts 30s timeout**
4. Agent processes → Returns result (1-2s) ✅
5. MCP server receives agent response ✅
6. **BUT**: If any delay occurs, MCP times out at 30s
7. **MCP promise rejects** → Handler throws error
8. ❌ **NO response sent to enrichment worker**
9. Enrichment worker waits 120-180s → times out

## Evidence

### From Logs:

**Entity Agent** (Working):
```
2026-01-26 09:13:17 - Extracting people from 19780 chars
2026-01-26 09:13:18 - Extracted 4 people  [1.4s processing]
```

**Structure Agent** (Working):
```
2026-01-26 09:13:13 - Parsing letter body structure  
2026-01-26 09:13:13 - Parsed 7 paragraphs  [<0.1s processing]
```

**MCP Server** (Receiving responses):
```
{"level":20,"msg":"✓ TRACE: Invocation response received","invocationId":"inv-xxx"}
{"level":30,"msg":"🔍 TRACE: Message is a response from agent"}
{"level":20,"msg":"✓ TRACE: Forwarding to response handler"}
```

**Enrichment Workers** (Timing out):
```
WARNING - ⚠️ Agent failed: entity-agent/extract_people with timeout: 
         Tool invocation timeout after 120s (attempt 3/4)
ERROR - ❌ Agent exhausted retries after 4 attempts (timeout)
```

## The Fix

### Option 1: Increase MCP Server Timeout (Recommended)

**File**: `enrichment_service/mcp_server/src/registry/tool-invoker.ts`

**Change line 38** from:
```typescript
private invocationTimeout: number = 30000; // 30 seconds default
```

To:
```typescript
private invocationTimeout: number = 200000; // 200 seconds (longer than worker timeout)
```

### Option 2: Make Timeout Configurable via Environment Variable

Add to constructor:
```typescript
constructor(
  private registry: ToolRegistry,
  private getAgentConnection: (agentId: string) => AgentConnection | undefined
) {
  super();
  this.invocationTimeout = parseInt(process.env.MCP_INVOCATION_TIMEOUT || '200000', 10);
}
```

Then set in docker-compose.yml:
```yaml
mcp-server:
  environment:
    - MCP_INVOCATION_TIMEOUT=200000
```

## Why 200 seconds?

- Entity agent timeout: 120s
- Structure agent timeout: 180s  
- Need buffer above these: **200s**
- Agents actually finish in 1-2s, so 200s is safe upper limit

## Steps to Apply Fix

1. **Edit the source file**:
   ```bash
   # Find the MCP server source location
   find . -name "tool-invoker.ts" -path "*/mcp_server/*"
   
   # Edit line 38 to increase timeout
   ```

2. **Rebuild MCP server**:
   ```bash
   docker compose build mcp-server
   ```

3. **Restart services**:
   ```bash
   docker compose restart mcp-server entity-agent structure-agent
   ```

4. **Test enrichment**:
   - Start a new bulk OCR job
   - Enrichment should complete without timeouts
   - ZIP should include enriched results

## Verification

After fix, check logs for:
```
✓ Model responded: entity-agent/extract_people completed in X.Xs
✓ Model responded: structure-agent/parse_letter_body completed in X.Xs  
✓ Phase 1 complete
✓ Enrichment saved to MongoDB
✓ ZIP regenerated with enrichment data
```

## Current Workaround

Enrichment will fail with timeouts. Users can:
1. Download OCR-only ZIP (works fine)
2. Wait for fix to get enrichment data
3. Manually regenerate ZIP after fixing MCP timeouts

---
**Status**: Root cause identified, fix documented  
**Priority**: High - blocks enrichment feature  
**Impact**: Enrichment never completes, ZIP missing enriched data
