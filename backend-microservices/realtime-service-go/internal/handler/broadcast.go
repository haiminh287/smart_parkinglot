package handler

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"

	"realtime-service/internal/hub"
)

// BroadcastHandler handles REST broadcast endpoints from other services
type BroadcastHandler struct {
	hub *hub.Hub
}

// NewBroadcastHandler creates a new BroadcastHandler
func NewBroadcastHandler(h *hub.Hub) *BroadcastHandler {
	return &BroadcastHandler{hub: h}
}

// BroadcastSlotStatus broadcasts slot status updates to parking_updates group
func (h *BroadcastHandler) BroadcastSlotStatus(c *gin.Context) {
	var data map[string]interface{}
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	h.hub.Broadcast("parking_updates", "slot.status_update", data)
	c.JSON(http.StatusOK, gin.H{"status": "broadcast sent"})
}

// BroadcastZoneAvailability broadcasts zone availability updates
func (h *BroadcastHandler) BroadcastZoneAvailability(c *gin.Context) {
	var data map[string]interface{}
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	h.hub.Broadcast("parking_updates", "zone.availability_update", data)
	c.JSON(http.StatusOK, gin.H{"status": "broadcast sent"})
}

// BroadcastLotAvailability broadcasts lot availability updates
func (h *BroadcastHandler) BroadcastLotAvailability(c *gin.Context) {
	var data map[string]interface{}
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	h.hub.Broadcast("parking_updates", "lot.availability_update", data)
	c.JSON(http.StatusOK, gin.H{"status": "broadcast sent"})
}

// BroadcastBookingUpdate broadcasts booking updates to a specific user
func (h *BroadcastHandler) BroadcastBookingUpdate(c *gin.Context) {
	var data struct {
		UserID string                 `json:"user_id"`
		Type   string                 `json:"type"`
		Data   map[string]interface{} `json:"data"`
	}
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if data.UserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id required"})
		return
	}

	msgType := data.Type
	if msgType == "" {
		msgType = "booking.status_update"
	}

	// Broadcast to user-specific channel
	group := fmt.Sprintf("user_%s", data.UserID)
	h.hub.Broadcast(group, msgType, data.Data)
	c.JSON(http.StatusOK, gin.H{"status": "broadcast sent"})
}

// BroadcastNotification broadcasts notification to a specific user
func (h *BroadcastHandler) BroadcastNotification(c *gin.Context) {
	var data struct {
		UserID string                 `json:"user_id"`
		Data   map[string]interface{} `json:"data"`
	}
	if err := c.ShouldBindJSON(&data); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if data.UserID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id required"})
		return
	}

	group := fmt.Sprintf("user_%s", data.UserID)
	h.hub.Broadcast(group, "notification", data.Data)
	c.JSON(http.StatusOK, gin.H{"status": "broadcast sent"})
}
