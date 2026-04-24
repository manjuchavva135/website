import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "@public-finance/shared-ts": path.resolve(__dirname, "../../packages/shared-ts/src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true
  }
});
