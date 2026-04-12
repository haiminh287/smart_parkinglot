package session

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// SessionData holds user session information stored in Redis
type SessionData struct {
	UserID  string `json:"user_id"`
	Email   string `json:"email"`
	Role    string `json:"role"`    // "user" or "admin"
	IsStaff bool   `json:"is_staff"`
}

// RedisStore manages sessions in Redis
type RedisStore struct {
	client *redis.Client
	ctx    context.Context
	ttl    time.Duration
}

// NewRedisStore creates a new Redis session store
func NewRedisStore(redisURL string) (*RedisStore, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("invalid redis URL: %w", err)
	}

	client := redis.NewClient(opts)
	ctx := context.Background()

	// Test connection
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis connection failed: %w", err)
	}

	return &RedisStore{
		client: client,
		ctx:    ctx,
		ttl:    7 * 24 * time.Hour, // 7 days session TTL
	}, nil
}

// CreateSession creates a new session and returns the session ID
func (s *RedisStore) CreateSession(data *SessionData) (string, error) {
	sessionID := uuid.New().String()
	key := fmt.Sprintf("gateway:session:%s", sessionID)

	jsonData, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("failed to marshal session data: %w", err)
	}

	if err := s.client.Set(s.ctx, key, jsonData, s.ttl).Err(); err != nil {
		return "", fmt.Errorf("failed to store session: %w", err)
	}

	return sessionID, nil
}

// GetSession retrieves session data by session ID
func (s *RedisStore) GetSession(sessionID string) (*SessionData, error) {
	key := fmt.Sprintf("gateway:session:%s", sessionID)

	data, err := s.client.Get(s.ctx, key).Result()
	if err == redis.Nil {
		return nil, nil // Session not found
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	var session SessionData
	if err := json.Unmarshal([]byte(data), &session); err != nil {
		return nil, fmt.Errorf("failed to unmarshal session: %w", err)
	}

	// Refresh TTL on access
	s.client.Expire(s.ctx, key, s.ttl)

	return &session, nil
}

// DeleteSession removes a session
func (s *RedisStore) DeleteSession(sessionID string) error {
	key := fmt.Sprintf("gateway:session:%s", sessionID)
	return s.client.Del(s.ctx, key).Err()
}

// Client returns the underlying Redis client for shared use
func (s *RedisStore) Client() *redis.Client {
	return s.client
}

// Close closes the Redis connection
func (s *RedisStore) Close() error {
	return s.client.Close()
}
