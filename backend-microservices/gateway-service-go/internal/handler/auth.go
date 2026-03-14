package handler

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"strings"
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

const (
	oauthErrorAuthFailed   = "auth_failed"
	oauthErrorInvalidState = "invalid_state"
	oauthErrorProvider     = "provider_error"
	oauthErrorInvalidReq   = "invalid_request"
	oauthErrorGateway      = "gateway_error"
)

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
	h.setSessionCookie(c, sessionID)

	// Return auth-service response
	c.Data(http.StatusOK, "application/json", body)
}

// HandleOAuthCallback handles social OAuth callback and creates gateway session
func (h *AuthHandler) HandleOAuthCallback(provider string, c *gin.Context) {
	code := c.Query("code")
	state := c.Query("state")

	if code == "" {
		h.redirectOAuthCallback(c, provider, oauthErrorInvalidReq)
		return
	}

	targetURL := h.cfg.AuthServiceURL + "/auth/" + provider + "/callback/"
	reqURL, err := url.Parse(targetURL)
	if err != nil {
		log.Printf("OAuth callback URL parse error: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorGateway)
		return
	}

	query := reqURL.Query()
	query.Set("code", code)
	if state != "" {
		query.Set("state", state)
	}
	reqURL.RawQuery = query.Encode()

	httpReq, err := http.NewRequest(http.MethodGet, reqURL.String(), nil)
	if err != nil {
		log.Printf("OAuth callback request create error: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorGateway)
		return
	}
	httpReq.Header.Set("X-Gateway-Secret", h.cfg.GatewaySecret)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(httpReq)
	if err != nil {
		log.Printf("Auth service OAuth callback error: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorAuthFailed)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Read auth callback response error: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorAuthFailed)
		return
	}

	var authResp map[string]interface{}
	if err := json.Unmarshal(body, &authResp); err != nil {
		log.Printf("Auth callback JSON parse error: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorAuthFailed)
		return
	}

	if resp.StatusCode != http.StatusOK {
		h.redirectOAuthCallback(c, provider, extractOAuthErrorCode(authResp))
		return
	}

	userData, ok := authResp["user"].(map[string]interface{})
	if !ok {
		userData = authResp
	}

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

	sessionData := &session.SessionData{
		UserID:  toString(userData["id"]),
		Email:   toString(userData["email"]),
		Role:    role,
		IsStaff: isStaff,
	}

	sessionID, err := h.store.CreateSession(sessionData)
	if err != nil {
		log.Printf("Failed to create oauth session: %v", err)
		h.redirectOAuthCallback(c, provider, oauthErrorAuthFailed)
		return
	}

	h.setSessionCookie(c, sessionID)
	h.redirectOAuthCallback(c, provider, "")
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
	h.clearSessionCookie(c)

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

func (h *AuthHandler) setSessionCookie(c *gin.Context, sessionID string) {
	c.SetSameSite(parseSameSite(h.cfg.SessionCookieSameSite))
	c.SetCookie(
		"session_id",
		sessionID,
		h.cfg.SessionCookieMaxAge,
		"/",
		h.cfg.SessionCookieDomain,
		h.cfg.SessionCookieSecure,
		true,
	)
}

func (h *AuthHandler) clearSessionCookie(c *gin.Context) {
	c.SetSameSite(parseSameSite(h.cfg.SessionCookieSameSite))
	c.SetCookie(
		"session_id",
		"",
		-1,
		"/",
		h.cfg.SessionCookieDomain,
		h.cfg.SessionCookieSecure,
		true,
	)
}

func parseSameSite(value string) http.SameSite {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "strict":
		return http.SameSiteStrictMode
	case "none":
		return http.SameSiteNoneMode
	default:
		return http.SameSiteLaxMode
	}
}

func extractOAuthErrorCode(body map[string]interface{}) string {
	if raw, ok := body["error"]; ok {
		if code, ok := raw.(string); ok {
			return normalizeOAuthErrorCode(code)
		}
	}
	if raw, ok := body["code"]; ok {
		if code, ok := raw.(string); ok {
			return normalizeOAuthErrorCode(code)
		}
	}
	return oauthErrorAuthFailed
}

func normalizeOAuthErrorCode(code string) string {
	switch strings.ToLower(strings.TrimSpace(code)) {
	case oauthErrorInvalidState:
		return oauthErrorInvalidState
	case oauthErrorProvider:
		return oauthErrorProvider
	case oauthErrorInvalidReq:
		return oauthErrorInvalidReq
	case oauthErrorGateway:
		return oauthErrorGateway
	default:
		return oauthErrorAuthFailed
	}
}

func (h *AuthHandler) redirectOAuthCallback(c *gin.Context, provider, errCode string) {
	redirectURL, err := url.Parse(h.cfg.FEAuthCallbackURL)
	if err != nil {
		fallbackURL := "/auth/callback"
		params := url.Values{}
		if provider != "" {
			params.Set("provider", provider)
		}
		if errCode != "" {
			params.Set("error", normalizeOAuthErrorCode(errCode))
		}
		if encoded := params.Encode(); encoded != "" {
			fallbackURL += "?" + encoded
		}
		c.Redirect(http.StatusFound, fallbackURL)
		return
	}

	params := redirectURL.Query()
	if provider != "" {
		params.Set("provider", provider)
	}
	if errCode != "" {
		params.Set("error", normalizeOAuthErrorCode(errCode))
	}
	redirectURL.RawQuery = params.Encode()
	c.Redirect(http.StatusFound, redirectURL.String())
}

func toString(v interface{}) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	if f, ok := v.(float64); ok {
		return strconv.FormatInt(int64(f), 10)
	}
	if n, ok := v.(json.Number); ok {
		return n.String()
	}
	b, _ := json.Marshal(v)
	return string(b)
}
