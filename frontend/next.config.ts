import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/admin/:path*", destination: `${backend}/admin/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
    ];
  },
};

export default nextConfig;
