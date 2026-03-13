package config

import (
	"os"
)

// Config holds all gateway configuration
type Config struct {
	Port          string
	GatewaySecret string
	RedisURL      string
	Debug         bool

	// Service URLs (internal Docker network)
	AuthServiceURL         string
	ParkingServiceURL      string
	VehicleServiceURL      string
	BookingServiceURL      string
	NotificationServiceURL string
	RealtimeServiceURL     string
	PaymentServiceURL      string
	AIServiceURL           string
	ChatbotServiceURL      string
}

// Load reads configuration from environment variables
func Load() *Config {
	return &Config{
		Port:          getEnv("PORT", "8000"),
		GatewaySecret: getEnv("GATEWAY_SECRET", "gateway-internal-secret-key"),
		RedisURL:      getEnv("REDIS_URL", "redis://localhost:6379/1"),
		Debug:         getEnv("DEBUG", "false") == "true",

		AuthServiceURL:         getEnv("AUTH_SERVICE_URL", "http://auth-service:8000"),
		ParkingServiceURL:      getEnv("PARKING_SERVICE_URL", "http://parking-service:8000"),
		VehicleServiceURL:      getEnv("VEHICLE_SERVICE_URL", "http://vehicle-service:8000"),
		BookingServiceURL:      getEnv("BOOKING_SERVICE_URL", "http://booking-service:8000"),
		NotificationServiceURL: getEnv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000"),
		RealtimeServiceURL:     getEnv("REALTIME_SERVICE_URL", "http://realtime-service:8000"),
		PaymentServiceURL:      getEnv("PAYMENT_SERVICE_URL", "http://payment-service:8000"),
		AIServiceURL:           getEnv("AI_SERVICE_URL", "http://ai-service:8000"),
		ChatbotServiceURL:      getEnv("CHATBOT_SERVICE_URL", "http://chatbot-service:8000"),
	}
}

// ServiceRoute maps path prefixes to service URLs
type ServiceRoute struct {
	Name    string
	URL     string
	Public  bool // If true, no auth required
}

// GetServiceRoute returns the target service for a given path
func (c *Config) GetServiceRoute(path string) *ServiceRoute {
	routes := []struct {
		prefix string
		route  ServiceRoute
	}{
		{"auth/", ServiceRoute{"auth", c.AuthServiceURL, true}},
		{"parking/", ServiceRoute{"parking", c.ParkingServiceURL, false}},
		{"vehicles/", ServiceRoute{"vehicle", c.VehicleServiceURL, false}},
		{"bookings/", ServiceRoute{"booking", c.BookingServiceURL, false}},
		{"incidents/", ServiceRoute{"booking", c.BookingServiceURL, false}},
		{"notifications/", ServiceRoute{"notification", c.NotificationServiceURL, false}},
		{"realtime/", ServiceRoute{"realtime", c.RealtimeServiceURL, false}},
		{"payments/", ServiceRoute{"payment", c.PaymentServiceURL, false}},
		{"ai/", ServiceRoute{"ai", c.AIServiceURL, false}},
		{"chatbot/", ServiceRoute{"chatbot", c.ChatbotServiceURL, false}},
	}

	for _, r := range routes {
		if len(path) >= len(r.prefix) && path[:len(r.prefix)] == r.prefix {
			return &r.route
		}
	}
	return nil
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
