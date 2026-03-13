package handler

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"gateway-service/internal/config"
	"gateway-service/internal/session"
)

// AuthHandler handles login/logout with gateway session management
type AuthHandler struct {
	cfg   *config.Config
	store *session.RedisStore
}

// NewAuthHandler creates a new AuthHandler
func NewAuthHandler(cfg *config.Config, store *session.RedisStore) *AuthHandler {
	return &AuthHandler{cfg: cfg, store: store}
}

// loginRequest represents the login payload
type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// HandleLogin authenticates with auth-service and creates a gateway session
func (h *AuthHandler) HandleLogin(c *gin.Context) {
	var req loginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Email and password required",
		})
		return
	}

	// Forward to auth-service
	targetURL := h.cfg.AuthServiceURL + "/auth/login/"
	payload, _ := json.Marshal(req)

	httpReq, err := http.NewRequest("POST", targetURL, bytes.NewBuffer(payload))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Gateway error"})
		return
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.ContentLength = int64(len(payload))

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(httpReq)
	if err != nil {
		log.Printf("Auth service error: %v", err)
		c.JSON(http.StatusBadGateway, gin.H{
			"error":   "Auth service unavailable",
			"service": "auth",
		})
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read response"})
		return
	}

	// If auth failed, forward the error response
	if resp.StatusCode != http.StatusOK {
		c.Data(resp.StatusCode, "application/json", body)
		return
	}

	// Parse auth-service response
	var authResp map[string]interface{}
	if err := json.Unmarshal(body, &authResp); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Invalid auth response"})
		return
	}

	// Extract user data
	userData, ok := authResp["user"].(map[string]interface{})
	if !ok {
		userData = authResp // auth-service might return user directly
	}

	// Determine role and is_staff
	role := "user"
	isStaff := false
	if r, ok := userData["role"].(string); ok {
		role = r
		isStaff = role == "admin"
	}
	if s, ok := userData["is_staff"].(bool); ok {
		isStaff = s
		if isStaff {
			role = "admin"
		}
	}

	// Create gateway session in Redis
	sessionData := &session.SessionData{
		UserID:  toString(userData["id"]),
		Email:   toString(userData["email"]),
		Role:    role,
		IsStaff: isStaff,
	}

	sessionID, err := h.store.CreateSession(sessionData)
	if err != nil {
		log.Printf("Failed to create session: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Session creation failed"})
		return
	}

	// Set session cookie
	c.SetCookie(
		"session_id", // name
		sessionID,    // value
		7*24*3600,    // maxAge (7 days)
		"/",          // path
		"",           // domain
		false,        // secure (set true in production with HTTPS)
		true,         // httpOnly
	)

	// Return auth-service response
	c.Data(http.StatusOK, "application/json", body)
}

// HandleLogout destroys the gateway session
func (h *AuthHandler) HandleLogout(c *gin.Context) {
	sessionID, _ := c.Cookie("session_id")

	// Delete session from Redis
	if sessionID != "" {
		if err := h.store.DeleteSession(sessionID); err != nil {
			log.Printf("Failed to delete session: %v", err)
		}
	}

	// Clear cookie
	c.SetCookie("session_id", "", -1, "/", "", false, true)

	// Also forward to auth-service
	targetURL := h.cfg.AuthServiceURL + "/auth/logout/"
	httpReq, _ := http.NewRequest("POST", targetURL, nil)
	httpReq.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 5 * time.Second}
	client.Do(httpReq) // Best-effort, ignore errors

	c.JSON(http.StatusOK, gin.H{
		"message": "Logged out successfully",
	})
}

// HandleGetMe returns the current user from auth-service using the session
func (h *AuthHandler) HandleGetMe(c *gin.Context) {
	// Session already validated by AuthMiddleware
	// Forward to auth-service with user context headers
	proxy := NewProxyHandler(h.cfg)
	proxy.HandleProxy(c)
}

// Helper functions

func jsonReader(data []byte) io.Reader {
	return io.NopCloser(io.Reader(byteReader(data)))
}

type byteReaderImpl struct {
	data []byte
	pos  int
}

func byteReader(data []byte) *byteReaderImpl {
	return &byteReaderImpl{data: data}
}

func (r *byteReaderImpl) Read(p []byte) (n int, err error) {
	if r.pos >= len(r.data) {
		return 0, io.EOF
	}
	n = copy(p, r.data[r.pos:])
	r.pos += n
	return n, nil
}

func toString(v interface{}) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	if f, ok := v.(float64); ok {
		return json.Number(json.Number(string(rune(int(f))))).String()
	}
	b, _ := json.Marshal(v)
	return string(b)
}
