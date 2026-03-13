package handler_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/handler"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// testConfig returns a minimal config for health handler tests
func testConfig() *config.Config {
	return &config.Config{
		AuthServiceURL:         "http://localhost:8001",
		BookingServiceURL:      "http://localhost:8002",
		ParkingServiceURL:      "http://localhost:8003",
		VehicleServiceURL:      "http://localhost:8004",
		NotificationServiceURL: "http://localhost:8005",
		RealtimeServiceURL:     "http://localhost:8006",
		PaymentServiceURL:      "http://localhost:8007",
		AIServiceURL:           "http://localhost:8009",
		ChatbotServiceURL:      "http://localhost:8008",
	}
}

func TestHealthCheck_Returns200(t *testing.T) {
	r := gin.New()
	h := handler.NewHealthHandler(testConfig())
	r.GET("/health/", h.HealthCheck)

	req := httptest.NewRequest(http.MethodGet, "/health/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("HealthCheck: expected 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	if body["status"] != "healthy" {
		t.Errorf("Expected status 'healthy', got '%v'", body["status"])
	}
	if body["service"] != "gateway-service" {
		t.Errorf("Expected service 'gateway-service', got '%v'", body["service"])
	}
	if body["version"] != "1.0.0" {
		t.Errorf("Expected version '1.0.0', got '%v'", body["version"])
	}
}

func TestReadinessCheck_Returns200(t *testing.T) {
	r := gin.New()
	h := handler.NewHealthHandler(testConfig())
	r.GET("/health/ready/", h.ReadinessCheck)

	req := httptest.NewRequest(http.MethodGet, "/health/ready/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("ReadinessCheck: expected 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	if body["status"] != "ready" {
		t.Errorf("Expected status 'ready', got '%v'", body["status"])
	}
}

func TestLivenessCheck_Returns200(t *testing.T) {
	r := gin.New()
	h := handler.NewHealthHandler(testConfig())
	r.GET("/health/live/", h.LivenessCheck)

	req := httptest.NewRequest(http.MethodGet, "/health/live/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("LivenessCheck: expected 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	if body["status"] != "alive" {
		t.Errorf("Expected status 'alive', got '%v'", body["status"])
	}
}
