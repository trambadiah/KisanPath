import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
