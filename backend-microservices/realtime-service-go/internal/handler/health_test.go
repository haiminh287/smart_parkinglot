package handler_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"realtime-service/internal/hub"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func TestHealthCheck_Returns200(t *testing.T) {
	h := hub.NewHub()
	go h.Run()
	defer h.Shutdown()

	r := gin.New()
	r.GET("/health/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":      "healthy",
			"service":     "realtime-service",
			"version":     "1.0.0",
			"connections": h.ConnectionCount(),
		})
	})

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
	if body["service"] != "realtime-service" {
		t.Errorf("Expected service 'realtime-service', got '%v'", body["service"])
	}
	if body["version"] != "1.0.0" {
		t.Errorf("Expected version '1.0.0', got '%v'", body["version"])
	}
}

func TestHealthCheck_ReportsZeroConnections(t *testing.T) {
	h := hub.NewHub()
	go h.Run()
	defer h.Shutdown()

	r := gin.New()
	r.GET("/health/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"connections": h.ConnectionCount(),
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/health/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	connections, ok := body["connections"].(float64)
	if !ok {
		t.Fatalf("Expected connections to be a number, got %T", body["connections"])
	}
	if connections != 0 {
		t.Errorf("Expected 0 connections on fresh hub, got %v", connections)
	}
}
