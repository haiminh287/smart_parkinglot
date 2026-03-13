package config

import "os"

// Config holds realtime service configuration
type Config struct {
	Port          string
	GatewaySecret string
	RedisURL      string
	Debug         bool
}

// Load reads configuration from environment variables
func Load() *Config {
	return &Config{
		Port:          getEnv("PORT", "8006"),
		GatewaySecret: getEnv("GATEWAY_SECRET", "gateway-internal-secret-key"),
		RedisURL:      getEnv("REDIS_URL", "redis://localhost:6379/5"),
		Debug:         getEnv("DEBUG", "false") == "true",
	}
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
