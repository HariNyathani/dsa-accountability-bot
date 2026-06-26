import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
      "/auth": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Raise the warning threshold — the vendor chunk legitimately exceeds 500KB.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React stack — cached across every deploy.
          react: ["react", "react-dom", "react-router-dom"],
          // Animation library — heavy but shared across all pages.
          motion: ["motion/react"],
          // Chart library — only needed on Analytics, Dashboard, Profile, Admin.
          recharts: ["recharts"],
        },
      },
    },
  },
});

