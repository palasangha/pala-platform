/**
 * Simple trace ID utilities for correlation across layers.
 */

export interface TraceContext {
  traceId: string;
}

/**
 * Generate a roughly unique, readable trace ID.
 */
export function generateTraceId(): string {
  return `trc-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Ensure a trace ID exists; generate if missing.
 */
export function ensureTraceId(traceId?: string): string {
  return traceId || generateTraceId();
}
