/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Disable ESLint during production builds
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const apiUrl =
      process.env.BACKEND_API_URL ||
      (process.env.NODE_ENV === 'production'
        ? 'http://reviewai-staging-alb-2013043867.us-east-1.elb.amazonaws.com'
        : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
