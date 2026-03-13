package hub

import (
	"encoding/json"
	"testing"
	"time"
)

// ─── Hub Lifecycle ──────────────────────────────────────────────────────────

func TestNewHub_Initializes(t *testing.T) {
	h := NewHub()
	if h == nil {
		t.Fatal("NewHub returned nil")
	}
	if h.groups == nil {
		t.Error("groups map not initialized")
	}
	if h.register == nil || h.unregister == nil || h.broadcast == nil {
		t.Error("channels not initialized")
	}
}

func TestHub_RunAndShutdown(t *testing.T) {
	h := NewHub()
	done := make(chan struct{})
	go func() {
		h.Run()
		close(done)
	}()

	h.Shutdown()

	select {
	case <-done:
		// Run() exited cleanly
	case <-time.After(2 * time.Second):
		t.Fatal("Hub.Run did not exit after Shutdown")
	}
}

// ─── Connection Management ──────────────────────────────────────────────────

func TestNewConnection(t *testing.T) {
	h := NewHub()
	conn := h.NewConnection()

	if conn == nil {
		t.Fatal("NewConnection returned nil")
	}
	if conn.Send == nil {
		t.Error("Send channel not initialized")
	}
	if conn.Groups == nil {
		t.Error("Groups map not initialized")
	}
	if conn.hub != h {
		t.Error("hub reference not set")
	}
}

func TestConnectionCount_EmptyHub(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	if count := h.ConnectionCount(); count != 0 {
		t.Errorf("Expected 0 connections, got %d", count)
	}
}

// ─── Register / Unregister ──────────────────────────────────────────────────

func TestRegister_ConnToGroup(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "parking_updates")

	// Give event loop time to process
	time.Sleep(50 * time.Millisecond)

	if !conn.Groups["parking_updates"] {
		t.Error("Connection not subscribed to parking_updates")
	}
}

func TestRegister_MultipleGroups(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "parking_updates")
	h.Register(conn, "user_123")

	time.Sleep(50 * time.Millisecond)

	if !conn.Groups["parking_updates"] {
		t.Error("Missing parking_updates group")
	}
	if !conn.Groups["user_123"] {
		t.Error("Missing user_123 group")
	}
}

func TestUnregister_RemovesFromGroup(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "parking_updates")
	time.Sleep(50 * time.Millisecond)

	h.Unregister(conn, "parking_updates")
	time.Sleep(50 * time.Millisecond)

	if conn.Groups["parking_updates"] {
		t.Error("Connection still in parking_updates after unregister")
	}
}

func TestRemoveConnection_CleansAllGroups(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "group_a")
	h.Register(conn, "group_b")
	time.Sleep(50 * time.Millisecond)

	h.RemoveConnection(conn)
	time.Sleep(50 * time.Millisecond)

	// Send channel should be closed
	_, ok := <-conn.Send
	if ok {
		t.Error("Send channel should be closed after RemoveConnection")
	}
}

// ─── Broadcast ──────────────────────────────────────────────────────────────

func TestBroadcast_SendsToGroup(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "parking_updates")
	time.Sleep(50 * time.Millisecond)

	h.Broadcast("parking_updates", "slot.status_update", map[string]string{
		"slot_id": "A-01",
		"status":  "occupied",
	})

	select {
	case msg := <-conn.Send:
		var parsed Message
		if err := json.Unmarshal(msg, &parsed); err != nil {
			t.Fatalf("Failed to unmarshal broadcast: %v", err)
		}
		if parsed.Type != "slot.status_update" {
			t.Errorf("Expected type slot.status_update, got %s", parsed.Type)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Timed out waiting for broadcast message")
	}
}

func TestBroadcast_DoesNotSendToOtherGroups(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	connA := h.NewConnection()
	connB := h.NewConnection()
	h.Register(connA, "group_a")
	h.Register(connB, "group_b")
	time.Sleep(50 * time.Millisecond)

	h.Broadcast("group_a", "test", "data")

	select {
	case <-connA.Send:
		// Expected
	case <-time.After(2 * time.Second):
		t.Fatal("connA should have received the broadcast")
	}

	select {
	case <-connB.Send:
		t.Error("connB should NOT have received the broadcast for group_a")
	case <-time.After(100 * time.Millisecond):
		// Expected — no message for connB
	}
}

func TestBroadcast_UserSpecificChannel(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn := h.NewConnection()
	h.Register(conn, "user_abc-123")
	time.Sleep(50 * time.Millisecond)

	h.Broadcast("user_abc-123", "booking.status_update", map[string]string{
		"booking_id": "bk-001",
		"status":     "checked_in",
	})

	select {
	case msg := <-conn.Send:
		var parsed Message
		if err := json.Unmarshal(msg, &parsed); err != nil {
			t.Fatalf("Failed to unmarshal: %v", err)
		}
		if parsed.Type != "booking.status_update" {
			t.Errorf("Expected booking.status_update, got %s", parsed.Type)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Timed out waiting for user broadcast")
	}
}

func TestBroadcast_MultipleConnsSameGroup(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	conn1 := h.NewConnection()
	conn2 := h.NewConnection()
	h.Register(conn1, "parking_updates")
	h.Register(conn2, "parking_updates")
	time.Sleep(50 * time.Millisecond)

	h.Broadcast("parking_updates", "lot.update", map[string]int{"available": 5})

	for _, conn := range []*Connection{conn1, conn2} {
		select {
		case msg := <-conn.Send:
			var parsed Message
			if err := json.Unmarshal(msg, &parsed); err != nil {
				t.Errorf("Unmarshal failed: %v", err)
			}
		case <-time.After(2 * time.Second):
			t.Error("Connection did not receive broadcast")
		}
	}
}

func TestBroadcast_NoSubscribers_NoPanic(t *testing.T) {
	h := NewHub()
	go h.Run()
	defer h.Shutdown()

	// Should not panic
	h.Broadcast("nonexistent_group", "test", "data")
	time.Sleep(50 * time.Millisecond)
}

// ─── Message Serialization ──────────────────────────────────────────────────

func TestMessage_JSON(t *testing.T) {
	msg := Message{
		Type: "slot.status_update",
		Data: map[string]string{"slot_id": "A-01"},
	}

	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("Marshal failed: %v", err)
	}

	var parsed Message
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if parsed.Type != "slot.status_update" {
		t.Errorf("Expected type slot.status_update, got %s", parsed.Type)
	}
}
