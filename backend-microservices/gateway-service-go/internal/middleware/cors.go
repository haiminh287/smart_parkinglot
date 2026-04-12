package middleware

import (
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
)

var localDevOrigins = []string{
	"http://localhost:8080",
	"http://localhost:5173",
}

var knownProductionOrigins = []string{
	"https://parksmart.ghepdoicaulong.shop",
}

func buildAllowedOrigins(cfg *config.Config) []string {
	origins := make([]string, 0, len(cfg.CORSAllowedOrigins)+len(localDevOrigins)+len(knownProductionOrigins))
	seen := make(map[string]struct{}, len(cfg.CORSAllowedOrigins)+len(localDevOrigins)+len(knownProductionOrigins))

	for _, origin := range cfg.CORSAllowedOrigins {
		trimmed := strings.TrimSpace(origin)
		if trimmed == "" {
			continue
		}
		if _, exists := seen[trimmed]; exists {
			continue
		}
		seen[trimmed] = struct{}{}
		origins = append(origins, trimmed)
	}

	// Always include known production origins regardless of environment
	for _, origin := range knownProductionOrigins {
		if _, exists := seen[origin]; exists {
			continue
		}
		seen[origin] = struct{}{}
		origins = append(origins, origin)
	}

	if strings.EqualFold(cfg.Environment, "production") {
		return origins
	}

	for _, origin := range localDevOrigins {
		if _, exists := seen[origin]; exists {
			continue
		}
		seen[origin] = struct{}{}
		origins = append(origins, origin)
	}

	return origins
}

// CORSMiddleware returns CORS middleware configuration
func CORSMiddleware(cfg *config.Config) gin.HandlerFunc {
	return cors.New(cors.Config{
		AllowOrigins:     buildAllowedOrigins(cfg),
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "Cookie", "X-Requested-With"},
		ExposeHeaders:    []string{"Content-Length", "Set-Cookie"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	})
}
