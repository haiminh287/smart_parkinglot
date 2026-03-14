package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/joho/godotenv"

	"gateway-service/internal/config"
	"gateway-service/internal/handler"
	"gateway-service/internal/middleware"
	"gateway-service/internal/router"
	"gateway-service/internal/session"
)

// func nameFunc(nameVar <type>) <type> {}
func main() {
	// Load .env file (ignore error in production where env vars are set directly)
	_ = godotenv.Load()
	// Load configuration
	cfg := config.Load()
	// Initialize Redis session store
	store, err := session.NewRedisStore(cfg.RedisURL)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer store.Close()

	// Initialize handlers
	proxyHandler := handler.NewProxyHandler(cfg)
	authHandler := handler.NewAuthHandler(cfg, store)
	healthHandler := handler.NewHealthHandler(cfg)

	// Setup router
	r := router.Setup(cfg, store, proxyHandler, authHandler, healthHandler)

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("Gateway service starting on :%s", cfg.Port)
		if err := r.Run(":" + cfg.Port); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	<-quit
	log.Println("Shutting down gateway service...")

	// Cleanup
	if err := middleware.CleanupRateLimiter(); err != nil {
		log.Printf("Rate limiter cleanup error: %v", err)
	}

	log.Println("Gateway service stopped")
}
