import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ['remark-gfm', 'remark-breaks'],
};

export default nextConfig;
