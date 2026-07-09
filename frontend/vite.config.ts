import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Proxies /api/* to the FastAPI backend during local dev so the frontend
// can call relative paths (see src/services/apiClient.ts) without CORS
// friction. In production, VITE_API_BASE_URL should point directly at
// the deployed backend instead.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
