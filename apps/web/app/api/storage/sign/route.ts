import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json(
    {
      error: 'Legacy /api/storage endpoints are deprecated. Use MCP storage-agent tools over WebSocket.'
    },
    { status: 410 }
  );
}
