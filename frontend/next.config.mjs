import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.join(__dirname, "src");

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    root: __dirname,
    resolveAlias: {
      "@": srcDir,
    },
  },
  webpack(config) {
    config.resolve.alias["@"] = srcDir;
    return config;
  },
};

export default nextConfig;
