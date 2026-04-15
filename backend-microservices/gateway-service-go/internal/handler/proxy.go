package handler

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/session"
)

// ProxyHandler forwards requests to downstream microservices
// with a shared transport for connection pooling.
type ProxyHandler struct {
	cfg       *config.Config
	transport *http.Transport
}

// NewProxyHandler creates a ProxyHandler with shared transport.
func NewProxyHandler(cfg *config.Config) *ProxyHandler {
	return &ProxyHandler{
		cfg: cfg,
		transport: &http.Transport{
			MaxIdleConns:        200,
			MaxIdleConnsPerHost: 50,
			IdleConnTimeout:     90 * time.Second,
			DialContext: (&net.Dialer{
				Timeout:   5 * time.Second,
				KeepAlive: 30 * time.Second,
			}).DialContext,
			ResponseHeaderTimeout: 60 * time.Second,
		},
	}
}

// HandleProxy forwards the request to the appropriate microservice
func (h *ProxyHandler) HandleProxy(c *gin.Context) {
	normalizedPath := config.NormalizeServicePath(c.Param("path"))

	// Get target service
	route := h.cfg.GetServiceRoute(normalizedPath)
	if route == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Service not found",
			"path":  normalizedPath,
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

	proxy.Transport = h.transport

	// Customize the Director to set the correct path and headers
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)

		// Set the path to include the service path prefix
		// Backend services expect: /auth/login/, /bookings/, etc.
		req.URL.Path = "/" + normalizedPath
		req.URL.RawQuery = c.Request.URL.RawQuery
		req.Host = targetURL.Host

		// Strip client-supplied identity headers to prevent header injection:
		// a malicious client could forge these to impersonate another user or
		// bypass gateway auth checks on downstream services.
		req.Header.Del("X-User-ID")
		req.Header.Del("X-User-Email")
		req.Header.Del("X-User-Role")
		req.Header.Del("X-User-Is-Staff")
		req.Header.Del("X-Gateway-Secret")

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
		log.Printf("Proxy error for %s -> %s: %v", normalizedPath, route.URL, err)
		body, _ := json.Marshal(map[string]string{
			"error":   "Service unavailable",
			"service": route.Name,
		})
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		w.Write(body)
	}

	// Modify response to handle cookies and redirect path normalization
	proxy.ModifyResponse = func(resp *http.Response) error {
		location := resp.Header.Get("Location")
		if location == "" {
			return nil
		}

		// Ensure redirects from downstream services keep public /api prefix
		// to avoid falling into frontend SPA fallback (/auth/* -> index.html).
		if strings.HasPrefix(location, "/") && !strings.HasPrefix(location, "/api/") && !strings.HasPrefix(location, "/ws/") {
			trimmed := strings.TrimPrefix(location, "/")
			resp.Header.Set("Location", fmt.Sprintf("/api/%s", trimmed))
		}

		return nil
	}

	// Serve the proxy
	proxy.ServeHTTP(c.Writer, c.Request)
}
