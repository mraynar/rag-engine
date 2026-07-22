/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow cross-origin requests from the backend during development
  async headers() {
    return [];
  },
};

module.exports = nextConfig;
