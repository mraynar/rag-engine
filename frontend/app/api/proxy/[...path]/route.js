/**
 * Next.js API Route Proxy — app/api/proxy/[...path]/route.js
 *
 * PURPOSE:
 *   - Forwards all frontend API calls to the FastAPI backend.
 *   - The real backend URL (BACKEND_INTERNAL_URL) lives only in server-side env.
 *   - The browser sees /api/proxy/... not http://backend:8001/...
 *   - This closes the security gap where localhost:8001 was visible in client bundle.
 *
 * USAGE (frontend):
 *   fetch(`/api/proxy/chat`, { method: 'POST', ... })
 *   → becomes → fetch(`http://backend:8001/chat`, { method: 'POST', ... }) server-side
 */

// BACKEND_INTERNAL_URL is a SERVER-SIDE ONLY variable (no NEXT_PUBLIC_ prefix).
// It is read at runtime on the server, never sent to the browser.
const BACKEND_INTERNAL_URL = process.env.BACKEND_INTERNAL_URL || 'http://localhost:8001';

/**
 * Unified request handler for all HTTP methods (GET, POST, PUT, PATCH, DELETE).
 * Receives a request at /api/proxy/<path> and forwards it to backend/<path>.
 */
async function handler(request, { params }) {
  // Resolve the full path segments (e.g. ['sources', '123', 'sync'])
  const pathSegments = (await params).path || [];
  const backendPath = pathSegments.join('/');

  // Preserve original query string
  const { searchParams } = new URL(request.url);
  const queryString = searchParams.toString();
  const targetUrl = `${BACKEND_INTERNAL_URL}/${backendPath}${queryString ? `?${queryString}` : ''}`;

  // Forward all original headers (including Authorization for Supabase JWT)
  const forwardHeaders = new Headers();
  for (const [key, value] of request.headers.entries()) {
    // Skip headers that would conflict or cause issues when proxying
    if (['host', 'connection', 'transfer-encoding'].includes(key.toLowerCase())) continue;
    forwardHeaders.set(key, value);
  }

  // Forward the request body for mutating methods
  let body = undefined;
  const method = request.method.toUpperCase();
  if (!['GET', 'HEAD'].includes(method)) {
    body = await request.blob();
  }

  try {
    const backendResponse = await fetch(targetUrl, {
      method,
      headers: forwardHeaders,
      body,
      // Don't follow redirects — pass them back to the client
      redirect: 'manual',
    });

    // Stream the backend response body back to the client
    const responseBody = await backendResponse.blob();

    // Forward response headers from backend
    const responseHeaders = new Headers();
    for (const [key, value] of backendResponse.headers.entries()) {
      // Skip headers that Next.js manages automatically
      if (['transfer-encoding', 'connection'].includes(key.toLowerCase())) continue;
      responseHeaders.set(key, value);
    }

    return new Response(responseBody, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error(`[Proxy] Failed to reach backend at ${targetUrl}:`, error);
    return new Response(
      JSON.stringify({ detail: 'Backend service is unavailable. Please try again later.' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Export handlers for all HTTP methods that the FastAPI backend uses
export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
