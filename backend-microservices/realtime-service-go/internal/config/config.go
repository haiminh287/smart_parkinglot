package config

import (
	"log"
	"os"
)

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
		GatewaySecret: mustGetEnv("GATEWAY_SECRET"),
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

func mustGetEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatalf("required env var %s not set", key)
	}
	return v
}
