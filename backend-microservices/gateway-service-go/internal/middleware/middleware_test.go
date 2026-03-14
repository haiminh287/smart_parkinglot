package middleware_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/middleware"
	"gateway-service/internal/session"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// ═══════════════════════════════════════════════════
// AUTH MIDDLEWARE TESTS
// ═══════════════════════════════════════════════════

func setupRouterWithAuth(store *session.RedisStore) *gin.Engine {
	cfg := config.Load()
	r := gin.New()
	r.Any("/*path", middleware.AuthMiddleware(cfg, store), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"user_id": c.Request.Header.Get("X-User-ID"),
			"email":   c.Request.Header.Get("X-User-Email"),
		})
	})
	return r
}

func TestAuthMiddleware_PublicEndpoint_NoSession(t *testing.T) {
	// Public endpoints (auth/*) should pass through without session
	cfg := config.Load()
	r := gin.New()
	r.Any("/*path", middleware.AuthMiddleware(cfg, nil), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "passed"})
	})

	req := httptest.NewRequest(http.MethodPost, "/auth/login/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Public endpoint auth/login/ should pass without session, got %d", w.Code)
	}
}

func TestAuthMiddleware_ProtectedEndpoint_NoSession(t *testing.T) {
	cfg := config.Load()
	r := gin.New()
	r.Any("/*path", middleware.AuthMiddleware(cfg, nil), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "should not reach"})
	})

	req := httptest.NewRequest(http.MethodGet, "/bookings/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Protected endpoint without session should return 401, got %d", w.Code)
	}

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	if body["detail"] == nil {
		t.Error("Unauthorized response should include 'detail' field")
	}
}

func TestAuthMiddleware_ProtectedEndpoint_InvalidCookie(t *testing.T) {
	cfg := config.Load()
	r := gin.New()
	r.Any("/*path", middleware.AuthMiddleware(cfg, nil), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "should not reach"})
	})

	req := httptest.NewRequest(http.MethodGet, "/vehicles/", nil)
	req.AddCookie(&http.Cookie{Name: "session_id", Value: "invalid-session"})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Invalid session cookie should return 401, got %d", w.Code)
	}
}

// ═══════════════════════════════════════════════════
// CORS MIDDLEWARE TESTS
// ═══════════════════════════════════════════════════

func TestCORSMiddleware_AllowsOrigin(t *testing.T) {
	r := gin.New()
	r.Use(middleware.CORSMiddleware(config.Load()))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req := httptest.NewRequest(http.MethodOptions, "/test", nil)
	req.Header.Set("Origin", "http://localhost:8080")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// CORS should handle preflight
	if w.Code != http.StatusOK && w.Code != http.StatusNoContent {
		t.Errorf("CORS preflight should succeed, got %d", w.Code)
	}
}

func TestCORSMiddleware_SetHeaders(t *testing.T) {
	r := gin.New()
	r.Use(middleware.CORSMiddleware(config.Load()))
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Origin", "http://localhost:8080")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	acaoHeader := w.Header().Get("Access-Control-Allow-Origin")
	if acaoHeader == "" {
		t.Error("CORS should set Access-Control-Allow-Origin header")
	}
}

// ═══════════════════════════════════════════════════
// RATE LIMIT MIDDLEWARE TESTS
// ═══════════════════════════════════════════════════

func TestRateLimitMiddleware_AllowsNormalTraffic(t *testing.T) {
	r := gin.New()
	r.Use(middleware.RateLimitMiddleware())
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	// Single request should pass
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.RemoteAddr = "192.168.1.1:12345"
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Normal traffic should pass rate limit, got %d", w.Code)
	}
}

// ═══════════════════════════════════════════════════
// LOGGING MIDDLEWARE TESTS
// ═══════════════════════════════════════════════════

func TestLoggingMiddleware_DoesNotBreakRequest(t *testing.T) {
	r := gin.New()
	r.Use(middleware.LoggingMiddleware())
	r.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"logged": true})
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Logging middleware should not break requests, got %d", w.Code)
	}
}
