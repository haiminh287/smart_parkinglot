package config

import (
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
)

// Config holds all gateway configuration
type Config struct {
	Port          string
	Environment   string
	GatewaySecret string
	RedisURL      string
	Debug         bool

	CORSAllowedOrigins    []string
	FEAuthCallbackURL     string
	SessionCookieDomain   string
	SessionCookieSecure   bool
	SessionCookieSameSite string
	SessionCookieMaxAge   int

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
	cfg := &Config{
		Port:          getEnv("PORT", "8000"),
		Environment:   getEnv("ENV", "development"),
		GatewaySecret: getEnv("GATEWAY_SECRET", "gateway-internal-secret-key"),
		RedisURL:      getEnv("REDIS_URL", "redis://localhost:6379/1"),
		Debug:         getEnv("DEBUG", "false") == "true",
		CORSAllowedOrigins: parseCSVEnv(
			"CORS_ALLOWED_ORIGINS",
			[]string{"http://localhost:5173", "http://localhost:3000", "http://localhost:8080"},
		),
		FEAuthCallbackURL:     getEnv("FE_AUTH_CALLBACK_URL", "http://localhost:5173/auth/callback"),
		SessionCookieDomain:   getEnv("SESSION_COOKIE_DOMAIN", ""),
		SessionCookieSecure:   getEnvAsBool("SESSION_COOKIE_SECURE", false),
		SessionCookieSameSite: getEnv("SESSION_COOKIE_SAMESITE", "Lax"),
		SessionCookieMaxAge:   getEnvAsInt("SESSION_COOKIE_MAX_AGE", 7*24*3600),

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

	if err := cfg.Validate(); err != nil {
		panic(err)
	}

	return cfg
}

func (c *Config) Validate() error {
	if strings.EqualFold(c.Environment, "production") {
		if strings.TrimSpace(c.SessionCookieDomain) == "" {
			return fmt.Errorf("SESSION_COOKIE_DOMAIN is required when ENV=production")
		}
		if !c.SessionCookieSecure {
			return fmt.Errorf("SESSION_COOKIE_SECURE must be true when ENV=production")
		}
		sameSite := strings.ToLower(strings.TrimSpace(c.SessionCookieSameSite))
		if sameSite != "lax" && sameSite != "strict" && sameSite != "none" {
			return fmt.Errorf("SESSION_COOKIE_SAMESITE must be one of Lax, Strict, None when ENV=production")
		}
		if len(c.CORSAllowedOrigins) == 0 {
			return fmt.Errorf("CORS_ALLOWED_ORIGINS is required when ENV=production")
		}
		for _, origin := range c.CORSAllowedOrigins {
			parsed, err := url.Parse(origin)
			if err != nil || parsed.Scheme == "" || parsed.Host == "" {
				return fmt.Errorf("invalid CORS origin: %s", origin)
			}
			host := strings.ToLower(parsed.Hostname())
			if parsed.Scheme != "https" {
				return fmt.Errorf("CORS origin must be https in production: %s", origin)
			}
			if host == "localhost" || host == "127.0.0.1" {
				return fmt.Errorf("CORS origin cannot be localhost in production: %s", origin)
			}
		}
		callbackURL, err := url.Parse(c.FEAuthCallbackURL)
		if err != nil || callbackURL.Scheme != "https" || callbackURL.Host == "" {
			return fmt.Errorf("FE_AUTH_CALLBACK_URL must be https when ENV=production")
		}
	}

	return nil
}

// ServiceRoute maps path prefixes to service URLs
type ServiceRoute struct {
	Name   string
	URL    string
	Public bool // If true, no auth required
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

func getEnvAsBool(key string, defaultValue bool) bool {
	value, exists := os.LookupEnv(key)
	if !exists {
		return defaultValue
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}

func getEnvAsInt(key string, defaultValue int) int {
	value, exists := os.LookupEnv(key)
	if !exists {
		return defaultValue
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}

func parseCSVEnv(key string, defaultValue []string) []string {
	raw, exists := os.LookupEnv(key)
	if !exists || strings.TrimSpace(raw) == "" {
		return defaultValue
	}

	parts := strings.Split(raw, ",")
	allowed := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed == "" {
			continue
		}
		allowed = append(allowed, trimmed)
	}

	if len(allowed) == 0 {
		return defaultValue
	}

	return allowed
}
