package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/joho/godotenv"

	"realtime-service/internal/config"
	"realtime-service/internal/handler"
	"realtime-service/internal/hub"
	"realtime-service/internal/middleware"

	"github.com/gin-gonic/gin"
	gincors "github.com/gin-contrib/cors"
	"time"
)

func main() {
	_ = godotenv.Load()

	cfg := config.Load()

	// Create and start the WebSocket hub
	h := hub.NewHub()
	go h.Run()

	// Setup Gin router
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}
	r := gin.New()
	r.Use(gin.Recovery())

	// CORS - allow WebSocket upgrade from frontend
	r.Use(gincors.New(gincors.Config{
		AllowOrigins:     []string{"http://localhost:5173", "http://localhost:3000", "http://localhost:8080"},
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "X-Gateway-Secret", "X-User-ID"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Health check
	r.GET("/health/", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":      "healthy",
			"service":     "realtime-service",
			"version":     "1.0.0",
			"connections": h.ConnectionCount(),
		})
	})

	// WebSocket endpoints
	wsHandler := handler.NewWSHandler(h)
	r.GET("/ws/parking/", wsHandler.HandleParkingWS)           // Public: parking updates
	r.GET("/ws/user/:userId/", wsHandler.HandleUserWS)         // Authenticated: user-specific updates

	// Broadcast API (internal only — requires X-Gateway-Secret)
	broadcast := r.Group("/api/broadcast")
	broadcast.Use(middleware.InternalAuthMiddleware(cfg))
	{
		broadcastHandler := handler.NewBroadcastHandler(h)
		broadcast.POST("/slot-status/", broadcastHandler.BroadcastSlotStatus)
		broadcast.POST("/zone-availability/", broadcastHandler.BroadcastZoneAvailability)
		broadcast.POST("/lot-availability/", broadcastHandler.BroadcastLotAvailability)
		broadcast.POST("/booking/", broadcastHandler.BroadcastBookingUpdate)
		broadcast.POST("/notification/", broadcastHandler.BroadcastNotification)
	}

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("Realtime service starting on :%s", cfg.Port)
		if err := r.Run(":" + cfg.Port); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	<-quit
	log.Println("Shutting down realtime service...")
	h.Shutdown()
	log.Println("Realtime service stopped")
}
