import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Parent D:\Orbit\package-lock.json makes Next treat the monorepo root as
  // the resolve context; pin CSS/JS package lookups back to frontend/.
  turbopack: {
    root: frontendRoot,
    resolveAlias: {
      tailwindcss: path.join(frontendRoot, "node_modules", "tailwindcss"),
      "@tailwindcss/postcss": path.join(
        frontendRoot,
        "node_modules",
        "@tailwindcss",
        "postcss",
      ),
    },
  },
  // Same root hint for non-Turbopack tracing / builds.
  outputFileTracingRoot: frontendRoot,
};

export default nextConfig;
