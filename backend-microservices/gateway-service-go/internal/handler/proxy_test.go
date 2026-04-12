package handler_test

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/handler"
)

// closeNotifierRecorder wraps httptest.ResponseRecorder with http.CloseNotifier
// support, required by httputil.ReverseProxy through gin.responseWriter.
type closeNotifierRecorder struct {
	*httptest.ResponseRecorder
	closed chan bool
}

func newCloseNotifierRecorder() *closeNotifierRecorder {
	return &closeNotifierRecorder{
		ResponseRecorder: httptest.NewRecorder(),
		closed:           make(chan bool, 1),
	}
}

func (c *closeNotifierRecorder) CloseNotify() <-chan bool {
	return c.closed
}

// ═══════════════════════════════════════════════════
// PROXY HANDLER TESTS
// ═══════════════════════════════════════════════════

func TestProxyHandler_ServiceNotFound(t *testing.T) {
	cfg := config.Load()
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/unknown/service/path/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("Unknown service path should return 404, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Response body should be valid JSON: %v", err)
	}
	if body["error"] != "Service not found" {
		t.Errorf("Expected 'Service not found' error, got '%v'", body["error"])
	}
}

func TestProxyHandler_AuthRoute(t *testing.T) {
	// Create a fake auth-service backend
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify gateway secret is injected
		gatewaySecret := r.Header.Get("X-Gateway-Secret")
		if gatewaySecret == "" {
			t.Error("Gateway secret should be injected into proxied request")
		}
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{
			"status": "proxied",
			"path":   r.URL.Path,
		})
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.AuthServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodPost, "/auth/login/", strings.NewReader(`{"email":"test@test.com"}`))
	req.Header.Set("Content-Type", "application/json")
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		body, _ := io.ReadAll(w.Body)
		t.Errorf("Auth proxy should return 200, got %d: %s", w.Code, string(body))
	}
}

func TestProxyHandler_BookingRoute(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify path is correct
		if !strings.HasPrefix(r.URL.Path, "/bookings") {
			t.Errorf("Expected path starting with /bookings, got %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.BookingServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/bookings/", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Booking proxy should return 200, got %d", w.Code)
	}
}

func TestProxyHandler_ApiParkingHealthRoute(t *testing.T) {
	var receivedPath string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedPath = r.URL.Path
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.ParkingServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/api/parking/health", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("API parking health proxy should return 200, got %d", w.Code)
	}
	if receivedPath != "/parking/health" {
		t.Errorf("Expected upstream path /parking/health, got %s", receivedPath)
	}
}

func TestProxyHandler_AiRoute(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ai-ok"})
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.AIServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/ai/metrics/", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("AI proxy should return 200, got %d", w.Code)
	}
}

func TestProxyHandler_ServiceDown_Returns502(t *testing.T) {
	cfg := config.Load()
	// Point to a non-existent service
	cfg.ParkingServiceURL = "http://127.0.0.1:19999"
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/parking/lots/", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadGateway {
		t.Errorf("Service down should return 502, got %d", w.Code)
	}
}

func TestProxyHandler_InjectsGatewaySecret(t *testing.T) {
	var receivedSecret string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedSecret = r.Header.Get("X-Gateway-Secret")
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.VehicleServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/vehicles/", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if receivedSecret != cfg.GatewaySecret {
		t.Errorf("Expected gateway secret '%s', got '%s'", cfg.GatewaySecret, receivedSecret)
	}
}

func TestProxyHandler_ForwardsQueryParams(t *testing.T) {
	var receivedQuery string
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedQuery = r.URL.RawQuery
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	cfg := config.Load()
	cfg.NotificationServiceURL = backend.URL
	proxyH := handler.NewProxyHandler(cfg)

	r := gin.New()
	r.Any("/*path", func(c *gin.Context) {
		proxyH.HandleProxy(c)
	})

	req := httptest.NewRequest(http.MethodGet, "/notifications/?page=1&page_size=10", nil)
	w := newCloseNotifierRecorder()
	r.ServeHTTP(w, req)

	if receivedQuery != "page=1&page_size=10" {
		t.Errorf("Query params should be forwarded, got '%s'", receivedQuery)
	}
}
