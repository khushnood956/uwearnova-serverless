import { type NextRequest, NextResponse } from 'next/server';
import { updateSession } from '@/lib/supabase/middleware';

/**
 * High-Performance Next.js Middleware for Supabase Auth
 * 
 * Performance Optimizations:
 * 1. Strict Matcher: Excludes all static assets, chunks, images, icons, and fonts.
 * 2. Prefetch Bypass: Immediately returns NextResponse.next() on Next.js Link prefetch requests
 *    (preventing 300ms network round-trips to remote Tokyo Supabase instance on link hover).
 * 3. Anonymous Visitor Fast-Path: Completely bypasses remote Supabase calls if no auth cookies
 *    exist (0ms latency overhead for all public browsing and unauthenticated portals).
 * 4. Authenticated Session Refresh: Synchronizes tokens only when an active auth cookie is present.
 */
export async function middleware(request: NextRequest) {
  // 1. FAST PATH: Instant bypass for Next.js link prefetch requests
  // Next.js automatically issues prefetches when <Link> components enter the viewport or are hovered.
  // We NEVER make blocking remote network calls on prefetch requests.
  const isPrefetch =
    request.headers.get('purpose') === 'prefetch' ||
    request.headers.get('next-router-prefetch') === '1' ||
    request.headers.get('x-middleware-prefetch') === '1';

  if (isPrefetch) {
    return NextResponse.next();
  }

  // 2. FAST PATH: If visitor has NO Supabase auth cookies, skip all remote calls.
  // There is no session to refresh or user to validate, avoiding 300ms Tokyo round-trips.
  const hasAuthCookie = request.cookies.getAll().some(
    (c) => c.name.startsWith('sb-') && c.name.endsWith('-auth-token')
  );

  if (!hasAuthCookie) {
    return NextResponse.next();
  }

  // 3. For visitors with active auth cookies, refresh session cookies and synchronize
  const { response } = await updateSession(request);
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - Public static assets (.svg, .png, .jpg, .jpeg, .gif, .webp, .ico, .css, .js, .map, .txt, .webmanifest)
     */
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|map|txt|webmanifest)$).*)',
  ],
};
