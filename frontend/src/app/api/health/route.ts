import { NextResponse } from 'next/server';

import { apiClient } from '@/lib/api/client';

/**
 * BFF health route. Fetches FastAPI server-side over loopback and relays the
 * result, proving TLS -> nginx -> Next.js -> FastAPI -> Postgres end to end.
 */
export async function GET() {
  const result = await apiClient.health();

  if (!result.success || !result.data) {
    return NextResponse.json(
      { error: result.error ?? 'health check failed' },
      { status: 503 }
    );
  }

  return NextResponse.json(result.data, { status: 200 });
}
