import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to the backend, so the browser never deals with CORS.
// Point VITE_BACKEND_URL at PC-B (e.g. http://192.168.1.20:8000) to use the shared demo server.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backend = env.VITE_BACKEND_URL || "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { "/api": backend, "/health": backend },
    },
  };
});
