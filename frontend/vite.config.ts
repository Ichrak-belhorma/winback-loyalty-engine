/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts is ~150 kB gzipped and lives in its own cacheable chunk.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: { manualChunks: { charts: ["recharts"] } },
    },
  },
  server: {
    // In dev, forward API calls to Django so the app is same-origin like in Docker.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
