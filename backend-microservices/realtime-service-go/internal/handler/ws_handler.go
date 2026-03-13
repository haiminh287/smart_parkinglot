package handler

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"realtime-service/internal/hub"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for development
	},
}

// WSHandler handles WebSocket connections
type WSHandler struct {
	hub *hub.Hub
}

// NewWSHandler creates a new WSHandler
func NewWSHandler(h *hub.Hub) *WSHandler {
	return &WSHandler{hub: h}
}

// HandleParkingWS handles public parking WebSocket connections
// All clients receive parking lot/zone/slot updates
func (h *WSHandler) HandleParkingWS(c *gin.Context) {
	ws, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	conn := h.hub.NewConnection()
	h.hub.AddConnection(conn)

	// Auto-subscribe to parking updates
	h.hub.Register(conn, "parking_updates")

	// Start read/write pumps
	go h.writePump(ws, conn)
	go h.readPump(ws, conn)
}

// HandleUserWS handles authenticated user WebSocket connections
// User receives personal booking/notification updates
func (h *WSHandler) HandleUserWS(c *gin.Context) {
	userID := c.Param("userId")
	if userID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "userId required"})
		return
	}

	ws, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	conn := h.hub.NewConnection()
	h.hub.AddConnection(conn)

	// Auto-subscribe to user-specific channel and parking updates
	h.hub.Register(conn, "user_"+userID)
	h.hub.Register(conn, "parking_updates")

	// Start read/write pumps
	go h.writePump(ws, conn)
	go h.readPump(ws, conn)
}

// readPump reads messages from the WebSocket connection
func (h *WSHandler) readPump(ws *websocket.Conn, conn *hub.Connection) {
	defer func() {
		h.hub.RemoveConnection(conn)
		ws.Close()
	}()

	ws.SetReadLimit(4096)
	ws.SetReadDeadline(time.Now().Add(60 * time.Second))
	ws.SetPongHandler(func(string) error {
		ws.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := ws.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
				log.Printf("WebSocket read error: %v", err)
			}
			break
		}

		// Parse client message
		var msg hub.Message
		if err := json.Unmarshal(message, &msg); err != nil {
			continue
		}

		// Handle client commands
		switch msg.Type {
		case "subscribe":
			if data, ok := msg.Data.(map[string]interface{}); ok {
				if channel, ok := data["channel"].(string); ok {
					h.hub.Register(conn, channel)
				}
			}
		case "unsubscribe":
			if data, ok := msg.Data.(map[string]interface{}); ok {
				if channel, ok := data["channel"].(string); ok {
					h.hub.Unregister(conn, channel)
				}
			}
		case "ping":
			// Respond with pong
			pong, _ := json.Marshal(hub.Message{Type: "pong", Data: map[string]interface{}{"timestamp": time.Now().Unix()}})
			conn.Send <- pong
		}
	}
}

// writePump writes messages to the WebSocket connection
func (h *WSHandler) writePump(ws *websocket.Conn, conn *hub.Connection) {
	ticker := time.NewTicker(30 * time.Second)
	defer func() {
		ticker.Stop()
		ws.Close()
	}()

	for {
		select {
		case message, ok := <-conn.Send:
			ws.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				ws.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := ws.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}

		case <-ticker.C:
			ws.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := ws.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}
