import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/generate":    "http://localhost:8001",
      "/progress":    "http://localhost:8001",
      "/output":      "http://localhost:8001",
      "/screenshots": "http://localhost:8001",
      "/assets":      "http://localhost:8001",
      "/video":       "http://localhost:8001",
      "/health":      "http://localhost:8001",
      "/templates":   "http://localhost:8001",
      "/styles":      "http://localhost:8001",
      "/test-voice":  "http://localhost:8001",
    },
  },
});
