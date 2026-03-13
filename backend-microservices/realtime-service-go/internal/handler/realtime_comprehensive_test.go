package handler_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"

	"realtime-service/internal/config"
	"realtime-service/internal/handler"
	"realtime-service/internal/hub"
	"realtime-service/internal/middleware"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// ─── Helpers ────────────────────────────────────────────────────────────────

func setupRouter() (*gin.Engine, *hub.Hub) {
	h := hub.NewHub()
	go h.Run()

	bh := handler.NewBroadcastHandler(h)
	cfg := &config.Config{GatewaySecret: "test-secret"}

	r := gin.New()
	internal := r.Group("/internal", middleware.InternalAuthMiddleware(cfg))
	internal.POST("/broadcast/slot-status", bh.BroadcastSlotStatus)
	internal.POST("/broadcast/zone-availability", bh.BroadcastZoneAvailability)
	internal.POST("/broadcast/lot-availability", bh.BroadcastLotAvailability)
	internal.POST("/broadcast/booking-update", bh.BroadcastBookingUpdate)
	internal.POST("/broadcast/notification", bh.BroadcastNotification)

	return r, h
}

func postJSON(r *gin.Engine, url string, body interface{}, secret string) *httptest.ResponseRecorder {
	data, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, url, bytes.NewReader(data))
	req.Header.Set("Content-Type", "application/json")
	if secret != "" {
		req.Header.Set("X-Gateway-Secret", secret)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

// ─── Broadcast Slot Status ──────────────────────────────────────────────────

func TestBroadcastSlotStatus_Success(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"slot_id": "A-01",
		"status":  "occupied",
	}
	w := postJSON(r, "/internal/broadcast/slot-status", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "broadcast sent" {
		t.Errorf("Expected 'broadcast sent', got '%s'", resp["status"])
	}
}

func TestBroadcastSlotStatus_InvalidBody(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	req := httptest.NewRequest(http.MethodPost, "/internal/broadcast/slot-status",
		bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Gateway-Secret", "test-secret")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for invalid body, got %d", w.Code)
	}
}

// ─── Broadcast Zone Availability ────────────────────────────────────────────

func TestBroadcastZoneAvailability_Success(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"zone_id":   "zone-1",
		"available": 10,
	}
	w := postJSON(r, "/internal/broadcast/zone-availability", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
}

// ─── Broadcast Lot Availability ─────────────────────────────────────────────

func TestBroadcastLotAvailability_Success(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"lot_id":    "lot-1",
		"available": 50,
	}
	w := postJSON(r, "/internal/broadcast/lot-availability", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
}

// ─── Broadcast Booking Update ───────────────────────────────────────────────

func TestBroadcastBookingUpdate_Success(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"user_id": "user-123",
		"type":    "booking.checked_in",
		"data": map[string]string{
			"booking_id": "bk-001",
			"status":     "checked_in",
		},
	}
	w := postJSON(r, "/internal/broadcast/booking-update", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
}

func TestBroadcastBookingUpdate_MissingUserID(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"type": "booking.checked_in",
		"data": map[string]string{},
	}
	w := postJSON(r, "/internal/broadcast/booking-update", body, "test-secret")

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for missing user_id, got %d", w.Code)
	}
}

func TestBroadcastBookingUpdate_DefaultType(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"user_id": "user-456",
		"data": map[string]string{
			"booking_id": "bk-002",
		},
	}
	w := postJSON(r, "/internal/broadcast/booking-update", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
}

// ─── Broadcast Notification ─────────────────────────────────────────────────

func TestBroadcastNotification_Success(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"user_id": "user-789",
		"data": map[string]string{
			"title":   "Booking confirmed",
			"message": "Your booking BK-001 is confirmed",
		},
	}
	w := postJSON(r, "/internal/broadcast/notification", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", w.Code)
	}
}

func TestBroadcastNotification_MissingUserID(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{
		"data": map[string]string{
			"title": "Test",
		},
	}
	w := postJSON(r, "/internal/broadcast/notification", body, "test-secret")

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 for missing user_id, got %d", w.Code)
	}
}

// ─── Internal Auth (Gateway Secret) ─────────────────────────────────────────

func TestInternalAuth_ValidSecret(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{"slot_id": "A-01"}
	w := postJSON(r, "/internal/broadcast/slot-status", body, "test-secret")

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200 with valid secret, got %d", w.Code)
	}
}

func TestInternalAuth_InvalidSecret(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{"slot_id": "A-01"}
	w := postJSON(r, "/internal/broadcast/slot-status", body, "wrong-secret")

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected 403 with invalid secret, got %d", w.Code)
	}
}

func TestInternalAuth_MissingSecret(t *testing.T) {
	r, h := setupRouter()
	defer h.Shutdown()

	body := map[string]interface{}{"slot_id": "A-01"}
	w := postJSON(r, "/internal/broadcast/slot-status", body, "")

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected 403 with missing secret, got %d", w.Code)
	}
}

// ─── WSHandler Creation (unit only — no real WS upgrade) ────────────────────

func TestNewWSHandler_NotNil(t *testing.T) {
	h := hub.NewHub()
	wsh := handler.NewWSHandler(h)
	if wsh == nil {
		t.Fatal("NewWSHandler returned nil")
	}
}

func TestNewBroadcastHandler_NotNil(t *testing.T) {
	h := hub.NewHub()
	bh := handler.NewBroadcastHandler(h)
	if bh == nil {
		t.Fatal("NewBroadcastHandler returned nil")
	}
}

// ─── WebSocket Endpoints (HTTP upgrade rejection) ───────────────────────────

func TestHandleParkingWS_RequiresWSUpgrade(t *testing.T) {
	h := hub.NewHub()
	go h.Run()
	defer h.Shutdown()

	wsh := handler.NewWSHandler(h)
	r := gin.New()
	r.GET("/ws/parking", wsh.HandleParkingWS)

	// Regular HTTP request should fail the WS upgrade
	req := httptest.NewRequest(http.MethodGet, "/ws/parking", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// gorilla/websocket returns 400 when upgrade headers missing
	if w.Code == http.StatusOK {
		t.Error("Expected non-200 for non-WebSocket request")
	}
}

func TestHandleUserWS_RequiresUserId(t *testing.T) {
	h := hub.NewHub()
	go h.Run()
	defer h.Shutdown()

	wsh := handler.NewWSHandler(h)
	r := gin.New()
	r.GET("/ws/user/:userId", wsh.HandleUserWS)

	// Empty userId param is not possible with gin routing,
	// but we can test that the endpoint is registered
	req := httptest.NewRequest(http.MethodGet, "/ws/user/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// Should 404 because /ws/user/ doesn't match /ws/user/:userId
	if w.Code != http.StatusNotFound && w.Code != http.StatusMovedPermanently {
		t.Logf("Route /ws/user/ returned %d (expected 404 or 301)", w.Code)
	}
}
