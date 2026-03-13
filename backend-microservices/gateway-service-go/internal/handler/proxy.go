package handler

import (
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/session"
)

// ProxyHandler forwards requests to downstream microservices
type ProxyHandler struct {
	cfg *config.Config
}

// NewProxyHandler creates a new ProxyHandler
func NewProxyHandler(cfg *config.Config) *ProxyHandler {
	return &ProxyHandler{cfg: cfg}
}

// HandleProxy forwards the request to the appropriate microservice
func (h *ProxyHandler) HandleProxy(c *gin.Context) {
	path := c.Param("path")
	if path != "" && path[0] == '/' {
		path = path[1:]
	}

	// Get target service
	route := h.cfg.GetServiceRoute(path)
	if route == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Service not found",
			"path":  path,
		})
		return
	}

	// Parse target URL
	targetURL, err := url.Parse(route.URL)
	if err != nil {
		log.Printf("Failed to parse service URL %s: %v", route.URL, err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Gateway configuration error",
		})
		return
	}

	// Create reverse proxy
	proxy := httputil.NewSingleHostReverseProxy(targetURL)

	// Customize the Director to set the correct path and headers
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)

		// Set the path to include the service path prefix
		// Backend services expect: /auth/login/, /bookings/, etc.
		req.URL.Path = "/" + path
		req.URL.RawQuery = c.Request.URL.RawQuery
		req.Host = targetURL.Host

		// Always inject gateway secret for inter-service auth
		req.Header.Set("X-Gateway-Secret", h.cfg.GatewaySecret)

		// Re-inject user context headers from gin context
		// (AuthMiddleware stores session_data; headers on c.Request may
		// not survive httputil.ReverseProxy's request cloning)
		if sd, ok := c.Get("session_data"); ok {
			if sessionData, ok := sd.(*session.SessionData); ok {
				req.Header.Set("X-User-ID", sessionData.UserID)
				req.Header.Set("X-User-Email", sessionData.Email)
				req.Header.Set("X-User-Role", sessionData.Role)
				if sessionData.IsStaff {
					req.Header.Set("X-User-Is-Staff", "true")
				} else {
					req.Header.Set("X-User-Is-Staff", "false")
				}
			}
		}

		// Remove hop-by-hop headers
		req.Header.Del("Connection")
		req.Header.Del("Upgrade")
	}

	// Handle errors
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("Proxy error for %s -> %s: %v", path, route.URL, err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		io.WriteString(w, `{"error":"Service unavailable","service":"`+route.Name+`"}`)
	}

	// Modify response to handle CORS and cookies
	proxy.ModifyResponse = func(resp *http.Response) error {
		// Copy Set-Cookie headers from downstream services
		// This allows auth-service cookies to pass through
		return nil
	}

	// Serve the proxy
	proxy.ServeHTTP(c.Writer, c.Request)
}

// HandleMultipartProxy handles multipart/form-data requests (file uploads)
func (h *ProxyHandler) HandleMultipartProxy(c *gin.Context) {
	// httputil.ReverseProxy handles multipart natively
	// No special handling needed — it forwards the raw body
	h.HandleProxy(c)
}

// stripPathPrefix removes the /api/ prefix from the path
func stripPathPrefix(path string) string {
	return strings.TrimPrefix(path, "/api/")
}
