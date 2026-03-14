package config_test

import (
	"os"
	"testing"

	"gateway-service/internal/config"
)

func TestLoad_DefaultValues(t *testing.T) {
	// Clear env vars to test defaults
	os.Unsetenv("PORT")
	os.Unsetenv("GATEWAY_SECRET")
	os.Unsetenv("REDIS_URL")

	cfg := config.Load()

	if cfg.Port != "8000" {
		t.Errorf("Expected default port '8000', got '%s'", cfg.Port)
	}
	if cfg.GatewaySecret != "gateway-internal-secret-key" {
		t.Errorf("Expected default gateway secret, got '%s'", cfg.GatewaySecret)
	}
	if cfg.RedisURL != "redis://localhost:6379/1" {
		t.Errorf("Expected default Redis URL with DB 1, got '%s'", cfg.RedisURL)
	}
}

func TestGetServiceRoute_ValidRoutes(t *testing.T) {
	cfg := config.Load()

	tests := []struct {
		path     string
		expected string
	}{
		{"auth/login/", "auth"},
		{"parking/lots/", "parking"},
		{"vehicles/", "vehicle"},
		{"bookings/123/", "booking"},
		{"incidents/", "booking"},
		{"notifications/", "notification"},
		{"realtime/ws/", "realtime"},
		{"payments/initiate/", "payment"},
		{"ai/detect/", "ai"},
		{"chatbot/chat/", "chatbot"},
	}

	for _, tt := range tests {
		route := cfg.GetServiceRoute(tt.path)
		if route == nil {
			t.Errorf("GetServiceRoute(%q) returned nil, expected route for '%s'", tt.path, tt.expected)
			continue
		}
		if route.Name != tt.expected {
			t.Errorf("GetServiceRoute(%q).Name = %q, want %q", tt.path, route.Name, tt.expected)
		}
	}
}

func TestGetServiceRoute_UnknownPath(t *testing.T) {
	cfg := config.Load()

	route := cfg.GetServiceRoute("unknown/path/")
	if route != nil {
		t.Errorf("GetServiceRoute(unknown) should return nil, got %+v", route)
	}
}

func TestGetServiceRoute_AuthIsPublic(t *testing.T) {
	cfg := config.Load()

	route := cfg.GetServiceRoute("auth/login/")
	if route == nil {
		t.Fatal("GetServiceRoute(auth) returned nil")
	}
	if !route.Public {
		t.Error("Auth route should be public")
	}
}

func TestGetServiceRoute_BookingsIsProtected(t *testing.T) {
	cfg := config.Load()

	route := cfg.GetServiceRoute("bookings/")
	if route == nil {
		t.Fatal("GetServiceRoute(bookings) returned nil")
	}
	if route.Public {
		t.Error("Bookings route should NOT be public")
	}
}

func TestValidate_ProductionRequiresCookieDomain(t *testing.T) {
	cfg := &config.Config{
		Environment:           "production",
		SessionCookieDomain:   "",
		SessionCookieSecure:   true,
		SessionCookieSameSite: "Lax",
		CORSAllowedOrigins:    []string{"https://app.example.com"},
		FEAuthCallbackURL:     "https://app.example.com/auth/callback",
	}

	if err := cfg.Validate(); err == nil {
		t.Fatal("expected validation error when SESSION_COOKIE_DOMAIN is missing")
	}
}

func TestValidate_ProductionRejectsInsecureCORSOrigin(t *testing.T) {
	cfg := &config.Config{
		Environment:           "production",
		SessionCookieDomain:   ".example.com",
		SessionCookieSecure:   true,
		SessionCookieSameSite: "Lax",
		CORSAllowedOrigins:    []string{"http://localhost:5173"},
		FEAuthCallbackURL:     "https://app.example.com/auth/callback",
	}

	if err := cfg.Validate(); err == nil {
		t.Fatal("expected validation error for insecure CORS origin")
	}
}

func TestValidate_ProductionValidConfig(t *testing.T) {
	cfg := &config.Config{
		Environment:           "production",
		SessionCookieDomain:   ".example.com",
		SessionCookieSecure:   true,
		SessionCookieSameSite: "Lax",
		CORSAllowedOrigins:    []string{"https://app.example.com"},
		FEAuthCallbackURL:     "https://app.example.com/auth/callback",
	}

	if err := cfg.Validate(); err != nil {
		t.Fatalf("expected valid production config, got error: %v", err)
	}
}
