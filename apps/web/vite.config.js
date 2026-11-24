import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": backend, "/datos": backend, "/ws": { target: backend, ws: true } },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/maplibre-gl") || id.includes("node_modules\\maplibre-gl")) return "maplibre";
          if (
            id.includes("node_modules/@deck.gl") ||
            id.includes("node_modules\\@deck.gl") ||
            id.includes("node_modules/@luma.gl") ||
            id.includes("node_modules\\@luma.gl") ||
            id.includes("node_modules/@loaders.gl") ||
            id.includes("node_modules\\@loaders.gl")
          ) {
            return "deckgl";
          }
          if (id.includes("node_modules")) return "vendor";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/__tests__/setup.js",
  },
});
