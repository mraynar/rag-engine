/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    /**
     * NEXT_PUBLIC_API_URL points to the Next.js API proxy (/api/proxy).
     * This means:
     *   - Browser requests always go to the SAME domain (no localhost:8001 exposed).
     *   - The Next.js server forwards the request to BACKEND_INTERNAL_URL server-side.
     *   - In production, /api/proxy is automatically served from the same host/port,
     *     so no backend URL is ever leaked to the client bundle.
     */
    NEXT_PUBLIC_API_URL: '/api/proxy',
  },
};

module.exports = nextConfig;
