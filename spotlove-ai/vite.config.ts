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

  let hasWarnedMissingGatewaySecret = false;

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
        // AI service endpoints go directly to local AI service (not via Docker gateway)
        "/api/ai": {
          target: aiServiceUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => {
              if (gatewaySecret) {
                proxyReq.setHeader("X-Gateway-Secret", gatewaySecret);
                return;
              }

              if (!hasWarnedMissingGatewaySecret) {
                hasWarnedMissingGatewaySecret = true;
                console.warn(
                  "[vite] VITE_GATEWAY_SECRET is not set; skipping X-Gateway-Secret header in development mode.",
                );
              }
            });
          },
        },
        "/api": {
          target: gatewayUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, ""), // Remove /api prefix, gateway routes by path
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
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
