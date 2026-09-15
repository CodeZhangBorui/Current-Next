import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Django Admin owns the trailing-slash convention. Let its redirects pass
  // through instead of having Next.js normalize the same request again.
  skipTrailingSlashRedirect: true,
  async redirects() {
    return [{ source: "/admin", destination: "/admin/", permanent: false }];
  },
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
