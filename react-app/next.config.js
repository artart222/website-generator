const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const assetPrefix = process.env.NEXT_PUBLIC_ASSET_PREFIX || "";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  basePath: basePath || undefined,
  assetPrefix: assetPrefix || undefined,
};

module.exports = nextConfig;
