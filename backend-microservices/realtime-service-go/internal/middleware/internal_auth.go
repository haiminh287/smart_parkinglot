package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"realtime-service/internal/config"
)

// InternalAuthMiddleware verifies X-Gateway-Secret for internal service calls
func InternalAuthMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		secret := c.GetHeader("X-Gateway-Secret")
		if secret != cfg.GatewaySecret {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{
				"error": "Forbidden: invalid gateway secret",
			})
			return
		}
		c.Next()
	}
}
