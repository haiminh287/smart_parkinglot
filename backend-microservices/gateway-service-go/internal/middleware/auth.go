package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/session"
)

// AuthMiddleware validates session and injects user context headers
func AuthMiddleware(cfg *config.Config, store *session.RedisStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		path := c.Param("path")
		if path != "" && path[0] == '/' {
			path = path[1:]
		}

		// Check if this is a public endpoint (auth endpoints)
		route := cfg.GetServiceRoute(path)
		isPublic := route != nil && route.Public

		// Get session ID from cookie
		sessionID, err := c.Cookie("session_id")
		if err != nil || sessionID == "" {
			if isPublic {
				// Public endpoint, no session — allow through without user context
				c.Next()
				return
			}
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"detail": "Authentication credentials were not provided.",
			})
			return
		}

		// Validate session in Redis
		if store == nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"detail": "Session store unavailable.",
			})
			return
		}
		sessionData, err := store.GetSession(sessionID)
		if err != nil || sessionData == nil {
			if isPublic {
				// Public endpoint, invalid session — allow through without user context
				c.Next()
				return
			}
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"detail": "Invalid or expired session.",
			})
			return
		}

		// Inject user context headers for downstream services
		c.Request.Header.Set("X-User-ID", sessionData.UserID)
		c.Request.Header.Set("X-User-Email", sessionData.Email)
		c.Request.Header.Set("X-User-Role", sessionData.Role)
		if sessionData.IsStaff {
			c.Request.Header.Set("X-User-Is-Staff", "true")
		} else {
			c.Request.Header.Set("X-User-Is-Staff", "false")
		}

		// Store session data in context for handlers
		c.Set("session_data", sessionData)
		c.Set("session_id", sessionID)

		c.Next()
	}
}
