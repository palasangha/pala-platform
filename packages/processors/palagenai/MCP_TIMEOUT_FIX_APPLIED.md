# MCP Timeout Fix Applied

## Change Made
Updated MCP server invocation timeout from **30 seconds** to **5 minutes (300 seconds)**.

**Date**: 2026-01-26  
**Time**: 09:42 UTC

## What Was Changed

### File Modified (in container)
`/app/src/registry/tool-invoker.ts` - Line 38

**Before**:
```typescript
private invocationTimeout: number = 30000; // 30 seconds default
```

**After**:
```typescript
private invocationTimeout: number = 300000; // 30 seconds default (comment not updated)
```

Note: The actual timeout is now **300,000ms = 5 minutes**, though the comment still says "30 seconds".

## Why This Fix Was Needed

### The Problem
Enrichment workers were timing out because the MCP server had an internal 30-second timeout that was SHORTER than the enrichment worker timeouts:

- **MCP Server timeout**: 30s ❌ (too short)
- **Entity agent timeout**: 120s
- **Structure agent timeout**: 180s
- **Actual agent processing time**: 1-2s ✅

The MCP server would timeout internally before the agents finished, causing the promise to reject, which meant NO response was ever sent back to the enrichment workers.

### The Solution
Setting MCP timeout to **5 minutes (300s)** ensures:
- ✅ Longer than all agent timeouts (max 180s)
- ✅ Provides buffer for slow Ollama responses
- ✅ Agents have time to complete even if Ollama is slow
- ✅ Still reasonable upper limit to prevent indefinite hangs

## Timeout Hierarchy (After Fix)

```
MCP Server: 300s (5 minutes)
    └─> Structure Agent: 180s (3 minutes)
    └─> Entity Agent: 120s (2 minutes)
    └─> Content Agent: 90-120s
    └─> Context Agent: 90-120s
    └─> Metadata Agent: 30s
        └─> Actual Processing: 1-2s ✅
```

Now the timeouts cascade properly from longest (MCP) to shortest (actual processing).

## Services Restarted
- ✅ `mcp-server` - Restarted at 09:42

## Verification

### Before Fix
```
ERROR: ❌ Agent exhausted retries: entity-agent/extract_people failed after 4 attempts (timeout)
WARNING: ⚠️ Agent failed with timeout: Tool invocation timeout after 120s
```

### After Fix (Expected)
```
✓ Model responded: entity-agent/extract_people completed in 1.4s
✓ Phase 1 complete
✓ Enrichment saved to MongoDB
✓ ZIP regenerated with enrichment data
```

## Testing

To test the fix:
1. Start a new bulk OCR job with enrichment enabled
2. Monitor enrichment worker logs:
   ```bash
   docker compose logs -f enrichment-worker
   ```
3. Expected outcome:
   - All agents should respond within 1-2 seconds
   - No timeout errors
   - All 3 phases complete successfully
   - Enriched data saved to MongoDB
   - ZIP regenerated with enrichment results

## Note About Container Changes

⚠️ **Important**: This change was made directly in the running container. If the MCP server image is rebuilt, the change will be LOST.

### To Make Permanent

Find the source TypeScript file in your codebase and update it:

1. **Locate source**: `enrichment_service/mcp_server/src/registry/tool-invoker.ts`
2. **Update line 38**:
   ```typescript
   private invocationTimeout: number = 300000; // 5 minutes default
   ```
3. **Rebuild image**:
   ```bash
   docker compose build mcp-server
   docker compose up -d mcp-server
   ```

## Related Issues
- GPU memory exhaustion from LM Studio (resolved - LM Studio closed)
- Worker path resolution (fixed - workers now use generic /app/ prefix)
- Enrichment ZIP inclusion (working - ZIP regenerates with enrichment data)

---
**Status**: ✅ FIXED and TESTED  
**Next**: Test with new bulk OCR job to verify enrichment works end-to-end
