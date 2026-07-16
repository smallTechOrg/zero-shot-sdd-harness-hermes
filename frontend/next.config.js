/**
 * Next.js config — static export, basePath=/app, images unoptimised.
 * Per harness/patterns/tech-stack.md §"Frontend Static-Export & Styling Rule"
 * the single-origin /app/ path is mandatory.
 */
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: "/app",
  images: { unoptimized: true },
  // Static export forbids server actions; opt-in clean.
  experimental: {
    // empty on purpose
  },
};

module.exports = nextConfig;
