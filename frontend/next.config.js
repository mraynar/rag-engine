/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // Next.js API proxy to hide internal backend port
    NEXT_PUBLIC_API_URL: '/api/proxy',
  },
};

module.exports = nextConfig;
