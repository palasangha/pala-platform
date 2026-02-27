/**
 * Storage Backends API Route
 * Lists available storage backends from Python backend
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function GET(request: NextRequest) {
  try {
    // Try to fetch from real Python backend first
    try {
      const response = await fetch(`${BACKEND_URL}/storage/backends`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch (err) {
      console.warn('Could not reach Python storage backend, using default');
    }

    // Fallback to default if Python backend is not available
    return NextResponse.json({
      backends: [
        {
          name: 'local-primary',
          type: 'LocalStorageBackend',
          is_default: true,
          enabled: true
        }
      ],
      default_backend: 'local-primary'
    });
  } catch (error) {
    return NextResponse.json(
      {
        backends: [
          {
            name: 'local-primary',
            type: 'LocalStorageBackend',
            is_default: true,
            enabled: true
          }
        ],
        default_backend: 'local-primary'
      },
      { status: 200 }
    );
  }
}
