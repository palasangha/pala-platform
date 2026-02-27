/**
 * Storage API Route - Store Document
 * Calls the real Python storage backend
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5001';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Call the real Python storage backend
    const response = await fetch(`${BACKEND_URL}/storage/store-document`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_id: body.job_id,
        file_index: body.file_index || 0,
        ocr_text: body.ocr_text || '',
        content_type: body.content_type || 'document',
        original_file_path: body.original_file_path,
        enriched_metadata: body.enriched_metadata || {},
        document_metadata: body.document_metadata || {},
        backend: body.backend,
        signature: body.signature || null,
        tags: body.tags || {},
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Storage API returned ${response.status}`);
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Storage error:', error);
    const message = error instanceof Error ? error.message : 'Failed to store document';
    return NextResponse.json(
      { error: message, isDuplicate: message.includes('already stored') },
      { status: 500 }
    );
  }
}
