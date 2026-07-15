/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: "/app",
  images: { unoptimized: true },
  distDir: "out",
};

module.exports = nextConfig;
