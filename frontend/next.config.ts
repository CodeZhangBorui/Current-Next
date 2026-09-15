import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Django Admin owns the trailing-slash convention. Do not add a Next.js
  // redirect here: `/admin/` must be proxied directly to Django.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      // The `(.*)` matcher also catches the bare `/admin` request.
      { source: "/admin/:path(.*)", destination: `${backend}/admin/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
    ];
  },
};

export default nextConfig;
