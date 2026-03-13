package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// RateLimiter is a simple token bucket rate limiter
type RateLimiter struct {
	mu       sync.Mutex
	visitors map[string]*visitor
	rate     int           // requests per window
	window   time.Duration // time window
}

type visitor struct {
	tokens    int
	lastReset time.Time
}

var limiter *RateLimiter

func init() {
	limiter = &RateLimiter{
		visitors: make(map[string]*visitor),
		rate:     100,            // 100 requests
		window:   1 * time.Minute, // per minute
	}

	// Cleanup old visitors periodically
	go func() {
		for {
			time.Sleep(5 * time.Minute)
			limiter.cleanup()
		}
	}()
}

// RateLimitMiddleware limits requests per IP
func RateLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		ip := c.ClientIP()

		if !limiter.allow(ip) {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
				"error":   "Rate limit exceeded",
				"message": "Too many requests. Please try again later.",
			})
			return
		}

		c.Next()
	}
}

func (rl *RateLimiter) allow(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	v, exists := rl.visitors[key]
	if !exists {
		rl.visitors[key] = &visitor{
			tokens:    rl.rate - 1,
			lastReset: time.Now(),
		}
		return true
	}

	// Reset tokens if window has passed
	if time.Since(v.lastReset) > rl.window {
		v.tokens = rl.rate - 1
		v.lastReset = time.Now()
		return true
	}

	if v.tokens <= 0 {
		return false
	}

	v.tokens--
	return true
}

func (rl *RateLimiter) cleanup() {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	for key, v := range rl.visitors {
		if time.Since(v.lastReset) > 2*rl.window {
			delete(rl.visitors, key)
		}
	}
}

// CleanupRateLimiter is called on shutdown
func CleanupRateLimiter() error {
	// Nothing to clean up for in-memory limiter
	return nil
}
