/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@public-finance/shared-ts"],
  async rewrites() {
    const apiTarget = process.env.API_PROXY_TARGET || "http://localhost:8000";
    return [
      { source: "/api/v1/:path*", destination: `${apiTarget}/api/v1/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        source: "/admin/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store",
          },
        ],
      },
      {
        source: "/(api|api-docs|methodology)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400",
          },
        ],
      },
      {
        source: "/health",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
