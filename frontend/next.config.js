/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001',
  },
  // Allow cross-origin requests from the backend during development
  async headers() {
    return [];
  },
};

module.exports = nextConfig;
