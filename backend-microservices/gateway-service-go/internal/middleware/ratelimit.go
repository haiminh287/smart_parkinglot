package middleware

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"

	"gateway-service/internal/config"
)

var rateLimitScript = redis.NewScript(`
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
return {current, ttl}
`)

// RateLimitMiddleware limits requests per IP using Redis
func RateLimitMiddleware(cfg *config.Config, rdb *redis.Client) gin.HandlerFunc {
	return func(c *gin.Context) {
		if !cfg.RateLimitEnabled {
			c.Next()
			return
		}

		ip := c.ClientIP()
		key := fmt.Sprintf("ratelimit:%s", ip)

		if rdb == nil {
			log.Printf("[WARN] Redis client is nil — allowing request")
			c.Next()
			return
		}

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		result, err := rateLimitScript.Run(ctx, rdb, []string{key}, cfg.RateLimitRequests, cfg.RateLimitWindow).Int64Slice()
		if err != nil {
			log.Printf("[WARN] Redis rate limit unavailable: %v — allowing request", err)
			c.Next()
			return
		}

		current := result[0]
		ttl := result[1]
		limit := int64(cfg.RateLimitRequests)
		remaining := limit - current
		if remaining < 0 {
			remaining = 0
		}

		c.Header("X-RateLimit-Limit", strconv.FormatInt(limit, 10))
		c.Header("X-RateLimit-Remaining", strconv.FormatInt(remaining, 10))
		c.Header("X-RateLimit-Reset", strconv.FormatInt(ttl, 10))

		if current > limit {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"success": false,
				"error": gin.H{
					"code":    "ERR_RATE_LIMIT",
					"message": "Too many requests. Please try again later.",
				},
			})
			return
		}

		c.Next()
	}
}

// CleanupRateLimiter is called on shutdown
func CleanupRateLimiter() error {
	return nil
}
