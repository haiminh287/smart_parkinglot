package config_test

import (
	"os"
	"testing"

	"gateway-service/internal/config"
)

func TestLoad_WithEnvSet(t *testing.T) {
	os.Setenv("GATEWAY_SECRET", "test-secret-value")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
	cfg := config.Load()
	if cfg.GatewaySecret != "test-secret-value" {
		t.Errorf("expected 'test-secret-value', got %q", cfg.GatewaySecret)
	}
}

func TestGetServiceRoute_ValidRoutes(t *testing.T) {
	os.Setenv("GATEWAY_SECRET", "test-secret")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
	cfg := config.Load()

	tests := []struct {
		path     string
		expected string
	}{
		{"auth/login/", "auth"},
		{"/api/auth/login/", "auth"},
		{"parking/lots/", "parking"},
		{"/api/parking/health", "parking"},
		{"vehicles/", "vehicle"},
		{"/api/vehicles/", "vehicle"},
		{"bookings/123/", "booking"},
		{"/api/bookings/123/", "booking"},
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
	os.Setenv("GATEWAY_SECRET", "test-secret")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
	cfg := config.Load()

	route := cfg.GetServiceRoute("unknown/path/")
	if route != nil {
		t.Errorf("GetServiceRoute(unknown) should return nil, got %+v", route)
	}
}

func TestGetServiceRoute_AuthIsPublic(t *testing.T) {
	os.Setenv("GATEWAY_SECRET", "test-secret")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
	cfg := config.Load()

	route := cfg.GetServiceRoute("auth/login/")
	if route == nil {
		t.Fatal("GetServiceRoute(auth) returned nil")
	}
	if !route.Public {
		t.Error("Auth route should be public")
	}
}

func TestGetServiceRoute_AdminIsProtected(t *testing.T) {
	os.Setenv("GATEWAY_SECRET", "test-secret")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
	cfg := config.Load()

	route := cfg.GetServiceRoute("auth/admin/users/")
	if route == nil {
		t.Fatal("GetServiceRoute(auth/admin) returned nil")
	}
	if route.Public {
		t.Error("Auth admin route should NOT be public — requires authentication")
	}
}

func TestGetServiceRoute_BookingsIsProtected(t *testing.T) {
	os.Setenv("GATEWAY_SECRET", "test-secret")
	t.Cleanup(func() { os.Unsetenv("GATEWAY_SECRET") })
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
