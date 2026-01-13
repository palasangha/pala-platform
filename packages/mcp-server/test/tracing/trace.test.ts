/**
 * Tests for tracing utilities
 */

import { describe, it, expect } from 'vitest';
import { generateTraceId, ensureTraceId } from '../../src/tracing';

describe('tracing', () => {
  it('should generate unique-ish trace IDs', () => {
    const id1 = generateTraceId();
    const id2 = generateTraceId();
    expect(id1).not.toBe(id2);
    expect(id1).toMatch(/^trc-/);
  });

  it('should return provided traceId when present', () => {
    const provided = 'custom-trace';
    expect(ensureTraceId(provided)).toBe(provided);
  });

  it('should generate when traceId missing', () => {
    const generated = ensureTraceId();
    expect(generated).toMatch(/^trc-/);
  });
});
