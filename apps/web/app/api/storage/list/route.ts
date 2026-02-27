/**
 * Storage API Route - List Documents
 * GET /api/storage/list
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    const response = await fetch(
      `${BACKEND_URL}/storage/list?${searchParams.toString()}`
    );

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(error, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to list documents';
    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
