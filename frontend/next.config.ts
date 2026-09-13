import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone with a self-contained server.js — required by
  // formava-web.service and by the multi-stage Dockerfile.
  output: "standalone",
};

export default nextConfig;
