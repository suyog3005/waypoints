/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disabled: React 18 StrictMode double-invokes effects in dev (mount →
  // cleanup → remount). MapLibre GL's WebGL context teardown/re-init inside
  // that double-invoke window leaves the second map instance's canvas in a
  // broken state where 'load' never fires (blank map, no errors). StrictMode
  // has no effect in production builds, so this only changes dev behavior.
  reactStrictMode: false,
};

export default nextConfig;
