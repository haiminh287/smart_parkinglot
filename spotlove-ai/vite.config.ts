import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const aiServiceUrl = env.VITE_AI_SERVICE_URL || "http://localhost:8009";
  const gatewayUrl = env.VITE_GATEWAY_URL || "http://localhost:8000";
  const gatewaySecret = env.VITE_GATEWAY_SECRET?.trim();
  const isDevelopment = mode === "development";

  if (!gatewaySecret && !isDevelopment) {
    throw new Error("VITE_GATEWAY_SECRET is required outside development mode");
  }

  return {
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
      // Proxy ALL API requests through Gateway service (port 8000)
      proxy: {
        // Camera streams go directly to AI service (no gateway auth for <img> tags)
        "/ai/cameras": {
          target: aiServiceUrl,
          changeOrigin: true,
          secure: false,
        },
        "/api": {
          target: gatewayUrl,
          changeOrigin: true,
          secure: false,
        },
        // WebSocket goes directly to realtime service
        "/ws": {
          target: "ws://localhost:8006",
          ws: true,
          changeOrigin: true,
        },
      },
    },
    plugins: [react(), mode === "development" && componentTagger()].filter(
      Boolean,
    ),
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router-dom"],
            "vendor-ui": [
              "@radix-ui/react-dialog",
              "@radix-ui/react-dropdown-menu",
              "@radix-ui/react-popover",
              "@radix-ui/react-select",
              "@radix-ui/react-tabs",
              "@radix-ui/react-toast",
              "@radix-ui/react-tooltip",
            ],
            "vendor-charts": ["recharts"],
            "vendor-redux": ["@reduxjs/toolkit", "react-redux"],
          },
        },
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
