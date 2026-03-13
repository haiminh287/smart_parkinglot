package hub

import (
	"encoding/json"
	"log"
	"sync"
)

// Message represents a WebSocket message
type Message struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
}

// Connection represents a WebSocket connection
type Connection struct {
	Send   chan []byte
	Groups map[string]bool
	hub    *Hub
}

// Subscription represents a subscribe/unsubscribe request
type Subscription struct {
	Conn  *Connection
	Group string
}

// BroadcastMessage represents a message to broadcast to a group
type BroadcastMessage struct {
	Group string
	Data  []byte
}

// Hub maintains the set of active connections and broadcasts messages
type Hub struct {
	// Groups mapped to their connections
	groups map[string]map[*Connection]bool

	// Register/unregister channels
	register   chan *Subscription
	unregister chan *Subscription

	// Broadcast channel
	broadcast chan *BroadcastMessage

	// Connection management
	addConn    chan *Connection
	removeConn chan *Connection

	mu   sync.RWMutex
	done chan struct{}
}

// NewHub creates a new Hub
func NewHub() *Hub {
	return &Hub{
		groups:     make(map[string]map[*Connection]bool),
		register:   make(chan *Subscription, 256),
		unregister: make(chan *Subscription, 256),
		broadcast:  make(chan *BroadcastMessage, 256),
		addConn:    make(chan *Connection, 256),
		removeConn: make(chan *Connection, 256),
		done:       make(chan struct{}),
	}
}

// Run starts the hub event loop
func (h *Hub) Run() {
	for {
		select {
		case <-h.done:
			return

		case conn := <-h.addConn:
			// New connection added, nothing special needed
			_ = conn

		case conn := <-h.removeConn:
			// Remove connection from all groups
			for group := range conn.Groups {
				if conns, ok := h.groups[group]; ok {
					delete(conns, conn)
					if len(conns) == 0 {
						delete(h.groups, group)
					}
				}
			}
			close(conn.Send)

		case sub := <-h.register:
			if _, ok := h.groups[sub.Group]; !ok {
				h.groups[sub.Group] = make(map[*Connection]bool)
			}
			h.groups[sub.Group][sub.Conn] = true
			sub.Conn.Groups[sub.Group] = true
			log.Printf("Connection subscribed to group: %s (total: %d)", sub.Group, len(h.groups[sub.Group]))

		case sub := <-h.unregister:
			if conns, ok := h.groups[sub.Group]; ok {
				delete(conns, sub.Conn)
				delete(sub.Conn.Groups, sub.Group)
				if len(conns) == 0 {
					delete(h.groups, sub.Group)
				}
			}

		case msg := <-h.broadcast:
			if conns, ok := h.groups[msg.Group]; ok {
				for conn := range conns {
					select {
					case conn.Send <- msg.Data:
					default:
						// Connection buffer full, remove it
						h.removeConn <- conn
					}
				}
				log.Printf("Broadcast to group %s: %d connections", msg.Group, len(conns))
			}
		}
	}
}

// Register adds a connection to a group
func (h *Hub) Register(conn *Connection, group string) {
	h.register <- &Subscription{Conn: conn, Group: group}
}

// Unregister removes a connection from a group
func (h *Hub) Unregister(conn *Connection, group string) {
	h.unregister <- &Subscription{Conn: conn, Group: group}
}

// Broadcast sends a message to all connections in a group
func (h *Hub) Broadcast(group string, msgType string, data interface{}) {
	msg := Message{Type: msgType, Data: data}
	jsonData, err := json.Marshal(msg)
	if err != nil {
		log.Printf("Failed to marshal broadcast message: %v", err)
		return
	}

	h.broadcast <- &BroadcastMessage{
		Group: group,
		Data:  jsonData,
	}
}

// AddConnection registers a new connection
func (h *Hub) AddConnection(conn *Connection) {
	h.addConn <- conn
}

// RemoveConnection removes a connection
func (h *Hub) RemoveConnection(conn *Connection) {
	h.removeConn <- conn
}

// NewConnection creates a new connection
func (h *Hub) NewConnection() *Connection {
	return &Connection{
		Send:   make(chan []byte, 256),
		Groups: make(map[string]bool),
		hub:    h,
	}
}

// ConnectionCount returns the total number of unique connections
func (h *Hub) ConnectionCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	unique := make(map[*Connection]bool)
	for _, conns := range h.groups {
		for conn := range conns {
			unique[conn] = true
		}
	}
	return len(unique)
}

// Shutdown stops the hub
func (h *Hub) Shutdown() {
	close(h.done)
}
