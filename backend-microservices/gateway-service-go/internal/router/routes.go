package router

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/handler"
	"gateway-service/internal/middleware"
	"gateway-service/internal/session"
)

// Setup configures the Gin router with all routes and middleware
func Setup(
	cfg *config.Config,
	store *session.RedisStore,
	proxyHandler *handler.ProxyHandler,
	authHandler *handler.AuthHandler,
	healthHandler *handler.HealthHandler,
) *gin.Engine {
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.New()

	// Global middleware
	r.Use(gin.Recovery())
	r.Use(middleware.CORSMiddleware(cfg))
	r.Use(middleware.LoggingMiddleware())
	r.Use(middleware.RateLimitMiddleware(cfg, store.Client()))

	// Single catch-all route handles health, auth, and proxied requests
	r.Any("/*path", func(c *gin.Context) {
		path := c.Param("path")
		normalizedPath := config.NormalizeServicePath(path)

		// Health check endpoints (bypass auth) — gateway-local and proxied service health
		isGatewayHealth := normalizedPath == "health/" || normalizedPath == "health" || strings.HasPrefix(normalizedPath, "health/")
		isServiceHealth := strings.HasSuffix(strings.TrimRight(normalizedPath, "/"), "health")
		if isGatewayHealth {
			switch normalizedPath {
			case "health/ready/", "health/ready":
				healthHandler.ReadinessCheck(c)
			case "health/live/", "health/live":
				healthHandler.LivenessCheck(c)
			case "health/services/", "health/services":
				healthHandler.ServicesHealth(c)
			default:
				healthHandler.HealthCheck(c)
			}
			return
		}
		if isServiceHealth {
			// Proxy to the upstream service health endpoint without auth
			proxyHandler.HandleProxy(c)
			return
		} // Auth special endpoints (no JWT required)
		cleanPath := normalizedPath
		method := c.Request.Method
		trimmedPath := strings.TrimSuffix(cleanPath, "/")
		if trimmedPath == "auth/refresh" || trimmedPath == "auth/token/refresh" {
			authHandler.HandleUnsupportedRefresh(c)
			return
		}
		if method == http.MethodPost {
			if cleanPath == "auth/login/" || cleanPath == "auth/login" {
				authHandler.HandleLogin(c)
				return
			}
			if cleanPath == "auth/logout/" || cleanPath == "auth/logout" {
				authHandler.HandleLogout(c)
				return
			}
		}
		if method == http.MethodGet {
			if cleanPath == "auth/google/callback/" || cleanPath == "auth/google/callback" {
				authHandler.HandleOAuthCallback("google", c)
				return
			}
		}

		// All other routes require JWT auth, then proxy
		middleware.AuthMiddleware(cfg, store)(c)
		if c.IsAborted() {
			return
		}
		proxyHandler.HandleProxy(c)
	})

	return r
}
