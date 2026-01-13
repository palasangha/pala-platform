/**
 * Network diagnostics utility
 * Helps diagnose connectivity and SSL issues
 */

interface DiagnosticResult {
  endpoint: string;
  method: 'GET' | 'OPTIONS';
  status: 'success' | 'failed' | 'timeout' | 'error';
  statusCode?: number;
  errorCode?: string;
  errorMessage?: string;
  duration: number;
  timestamp: string;
}

export const networkDiagnostics = {
  /**
   * Test a simple GET request without authentication
   */
  async testSimpleGet(url: string, timeout = 5000): Promise<DiagnosticResult> {
    const startTime = performance.now();
    const timestamp = new Date().toISOString();

    try {
      console.log(`[DIAG] Testing GET ${url} with ${timeout}ms timeout`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const duration = performance.now() - startTime;

      console.log(`[DIAG] GET ${url} - Status: ${response.status} (${duration.toFixed(0)}ms)`);

      return {
        endpoint: url,
        method: 'GET',
        status: response.ok ? 'success' : 'failed',
        statusCode: response.status,
        duration,
        timestamp,
      };
    } catch (error: any) {
      const duration = performance.now() - startTime;
      const errorCode = error.code || error.name;
      const errorMessage = error.message;

      console.error(`[DIAG] GET ${url} - Error: ${errorCode} - ${errorMessage} (${duration.toFixed(0)}ms)`);

      return {
        endpoint: url,
        method: 'GET',
        status: error.name === 'AbortError' ? 'timeout' : 'error',
        errorCode,
        errorMessage,
        duration,
        timestamp,
      };
    }
  },

  /**
   * Test CORS preflight (OPTIONS request)
   */
  async testCORSPreflight(url: string, timeout = 5000): Promise<DiagnosticResult> {
    const startTime = performance.now();
    const timestamp = new Date().toISOString();

    try {
      console.log(`[DIAG] Testing CORS preflight OPTIONS ${url}`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method: 'OPTIONS',
        headers: {
          'Access-Control-Request-Method': 'GET',
          'Access-Control-Request-Headers': 'content-type,authorization',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const duration = performance.now() - startTime;

      console.log(`[DIAG] OPTIONS ${url} - Status: ${response.status} (${duration.toFixed(0)}ms)`);

      return {
        endpoint: url,
        method: 'OPTIONS',
        status: response.ok ? 'success' : 'failed',
        statusCode: response.status,
        duration,
        timestamp,
      };
    } catch (error: any) {
      const duration = performance.now() - startTime;
      const errorCode = error.code || error.name;
      const errorMessage = error.message;

      console.error(`[DIAG] OPTIONS ${url} - Error: ${errorCode} - ${errorMessage} (${duration.toFixed(0)}ms)`);

      return {
        endpoint: url,
        method: 'OPTIONS',
        status: error.name === 'AbortError' ? 'timeout' : 'error',
        errorCode,
        errorMessage,
        duration,
        timestamp,
      };
    }
  },

  /**
   * Run full diagnostics for an endpoint
   */
  async runFullDiagnostics(endpoint: string): Promise<DiagnosticResult[]> {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`[DIAG] Starting full diagnostics for: ${endpoint}`);
    console.log(`${'='.repeat(60)}\n`);

    const results: DiagnosticResult[] = [];

    // Test 1: CORS Preflight
    console.log('[DIAG] Test 1/2: CORS Preflight (OPTIONS)');
    results.push(await this.testCORSPreflight(endpoint));
    console.log('');

    // Test 2: Simple GET
    console.log('[DIAG] Test 2/2: Simple GET');
    results.push(await this.testSimpleGet(endpoint));
    console.log('');

    // Summary
    console.log(`${'='.repeat(60)}`);
    console.log('[DIAG] Diagnostics Summary:');
    console.log(`${'='.repeat(60)}`);
    results.forEach((result, idx) => {
      const icon = result.status === 'success' ? '✓' : '✗';
      console.log(
        `[${idx + 1}] ${icon} ${result.method} ${result.endpoint}`
      );
      if (result.statusCode) {
        console.log(`    Status Code: ${result.statusCode}`);
      }
      if (result.errorCode) {
        console.log(`    Error: ${result.errorCode} - ${result.errorMessage}`);
      }
      console.log(`    Duration: ${result.duration.toFixed(0)}ms`);
    });
    console.log(`${'='.repeat(60)}\n`);

    return results;
  },

  /**
   * Get diagnostic information about the current environment
   */
  getEnvironmentInfo() {
    const info = {
      currentURL: window.location.href,
      protocol: window.location.protocol,
      hostname: window.location.hostname,
      port: window.location.port,
      origin: window.location.origin,
      userAgent: navigator.userAgent,
      onLine: navigator.onLine,
      timestamp: new Date().toISOString(),
    };

    console.log('[DIAG] Environment Information:');
    console.log(info);
    return info;
  },
};

export default networkDiagnostics;
