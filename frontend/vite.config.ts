import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          ui: ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-tabs", "@radix-ui/react-tooltip", "@radix-ui/react-toast", "@radix-ui/react-select", "@radix-ui/react-scroll-area", "@radix-ui/react-separator", "@radix-ui/react-switch", "@radix-ui/react-avatar", "@radix-ui/react-progress", "@radix-ui/react-label"],
          charts: ["recharts"],
          query: ["@tanstack/react-query"],
          markdown: ["react-markdown", "remark-gfm"],
          motion: ["framer-motion"],
          forms: ["react-hook-form", "@hookform/resolvers", "zod"],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
    cssCodeSplit: true,
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
});
