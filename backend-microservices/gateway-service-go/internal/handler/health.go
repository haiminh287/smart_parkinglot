package handler

import (
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
)

// HealthHandler handles health check endpoints
type HealthHandler struct {
	cfg *config.Config
}

// NewHealthHandler creates a new HealthHandler
func NewHealthHandler(cfg *config.Config) *HealthHandler {
	return &HealthHandler{cfg: cfg}
}

// HealthCheck returns service health status
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "gateway-service",
		"version": "1.0.0",
	})
}

// ReadinessCheck returns service readiness status
func (h *HealthHandler) ReadinessCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ready",
	})
}

// LivenessCheck returns service liveness status
func (h *HealthHandler) LivenessCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "alive",
	})
}

// serviceHealth holds the result of a downstream health check
type serviceHealth struct {
	Name   string `json:"name"`
	URL    string `json:"url"`
	Status string `json:"status"`
	Code   int    `json:"status_code"`
}

// ServicesHealth aggregates health from all downstream services
func (h *HealthHandler) ServicesHealth(c *gin.Context) {
	services := []struct {
		name string
		url  string
	}{
		{"auth-service", h.cfg.AuthServiceURL},
		{"booking-service", h.cfg.BookingServiceURL},
		{"parking-service", h.cfg.ParkingServiceURL},
		{"vehicle-service", h.cfg.VehicleServiceURL},
		{"notification-service", h.cfg.NotificationServiceURL},
		{"realtime-service", h.cfg.RealtimeServiceURL},
		{"payment-service", h.cfg.PaymentServiceURL},
		{"ai-service", h.cfg.AIServiceURL},
		{"chatbot-service", h.cfg.ChatbotServiceURL},
	}

	results := make([]serviceHealth, len(services))
	var wg sync.WaitGroup

	httpClient := &http.Client{Timeout: 3 * time.Second}

	for i, svc := range services {
		wg.Add(1)
		go func(idx int, name, url string) {
			defer wg.Done()
			healthURL := fmt.Sprintf("%s/health/", url)
			result := serviceHealth{Name: name, URL: healthURL, Status: "unhealthy", Code: 0}

			resp, err := httpClient.Get(healthURL)
			if err != nil {
				result.Status = "unreachable"
			} else {
				defer resp.Body.Close()
				result.Code = resp.StatusCode
				if resp.StatusCode == http.StatusOK {
					result.Status = "healthy"
				}
			}
			results[idx] = result
		}(i, svc.name, svc.url)
	}

	wg.Wait()

	allHealthy := true
	for _, r := range results {
		if r.Status != "healthy" {
			allHealthy = false
			break
		}
	}

	overallStatus := "healthy"
	httpStatus := http.StatusOK
	if !allHealthy {
		overallStatus = "degraded"
		httpStatus = http.StatusServiceUnavailable
	}

	c.JSON(httpStatus, gin.H{
		"status":   overallStatus,
		"gateway":  "healthy",
		"services": results,
	})
}
