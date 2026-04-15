# 🎮 Unity ParkSmart Simulator — Testing Guide

> **Cập nhật**: 2026-04-09  
> **Backend status**: ✅ All services running (16 containers)  
> **Booking status**: ✅ Pre-created and checked-in

---

## Booking Information (Pre-created)

| Field           | Value                                  |
| --------------- | -------------------------------------- |
| Booking ID      | `e9acc649-a4d6-4930-a1fb-b98ff0d6d267` |
| License Plate   | `51A-999.88`                           |
| Vehicle Type    | Car                                    |
| Floor           | Tầng 2 (level 2)                       |
| Zone            | Zone C                                 |
| Slot            | C-02                                   |
| Check-in Status | `checked_in`                           |

**QR Data:**

```json
{
  "booking_id": "e9acc649-a4d6-4930-a1fb-b98ff0d6d267",
  "user_id": "9084eb49-5094-4999-8448-150fe7a8c30e",
  "timestamp": "2026-04-09T02:29:56.282969+00:00"
}
```

---

## Step 1: Configure Unity API

Open Unity project: `ParkingSimulatorUnity/`

Find and verify `ApiConfig` (or similar ScriptableObject/MonoBehaviour) settings:

### Local Development

| Setting        | Value                                              |
| -------------- | -------------------------------------------------- |
| API Base URL   | `http://localhost:8000/api`                        |
| WebSocket URL  | `ws://localhost:8006/ws`                           |
| Gateway Secret | `<from .env — see .env.example>` |

### Cloudflare Domain (Production)

| Setting       | Value                                       |
| ------------- | ------------------------------------------- |
| API Base URL  | `https://parksmart.ghepdoicaulong.shop/api` |
| WebSocket URL | `wss://parksmart.ghepdoicaulong.shop/ws`    |

---

## Step 2: Launch Unity Scene

1. Open `ParkingSimulatorUnity.sln` in Unity Editor
2. Navigate to the main parking simulation scene
3. Select **Floor 2** (Tầng 2) view from the floor selector
4. You should see the parking lot layout with **Zone C** and **Zone D**

---

## Step 3: Observe Booking Loading

The simulator should automatically:

1. Fetch active bookings from `GET /api/bookings/`
2. Load the pre-created booking (`e9acc649`)
3. Show slot **C-02** as "reserved" on the floor map

---

## Step 4: Simulate Car Entry

1. A car with plate `51A-999.88` should spawn at the gate area
2. The car approaches **GATE-IN**
3. QR code scanning animation plays
4. The simulator sends QR data to ESP32 check-in endpoint:

```
POST /api/ai/parking/esp32/check-in/

{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"e9acc649-a4d6-4930-a1fb-b98ff0d6d267\",\"user_id\":\"9084eb49-5094-4999-8448-150fe7a8c30e\",\"timestamp\":\"2026-04-09T02:29:56.282969+00:00\"}"
}
```

5. AI plate recognition runs (plate camera capture or virtual camera)
6. Response: `barrier_action = "open"`
7. Gate barrier opens → car enters

> **⚠️ Note**: The booking is already `checked_in` (we did it via API test). The simulator may show it as already checked-in. If you need a fresh booking, see [Creating a New Booking](#creating-a-new-booking-if-needed).

---

## Step 5: Car Parks at Slot C-02

1. Car navigates through the parking lot to **Floor 2, Zone C**
2. Car parks at slot **C-02**
3. Slot status updates to "occupied" in real-time

---

## Step 6: Camera Overview (AI Detection)

If the simulator has a camera overview feature:

1. The overhead camera captures the parking floor
2. Frame is sent to `POST /api/ai/parking/detect-occupancy/` with slot bounding boxes
3. AI (YOLO11n) analyzes each slot for vehicle presence
4. Results update slot statuses in real-time on the floor map

**Example request:**

```json
{
  "camera_id": "CAM-FLOOR2-01",
  "image": "<base64-encoded frame>",
  "slots": [
    {
      "slot_id": "76cb49d0-ab57-46d8-95ed-03de54f6668a",
      "label": "C-02",
      "bbox": [x1, y1, x2, y2]
    }
  ]
}
```

---

## Step 7: Check-Out Flow (Optional)

To test check-out:

1. Car approaches **GATE-OUT**
2. QR code scanning
3. Send request:

```
POST /api/ai/parking/esp32/check-out/

{
  "gate_id": "GATE-OUT-01",
  "qr_data": "<QR JSON string>"
}
```

4. Payment calculated (if needed)
5. Barrier opens → car exits

---

## Creating a New Booking (if needed)

If you need a fresh `not_checked_in` booking:

```python
import requests, json
from datetime import datetime, timedelta, timezone

s = requests.Session()
s.post('http://localhost:8000/api/auth/login/', json={
    'email': 'e2e_playwright@parksmart.com',
    'password': 'TestPass123!'
})

tz = timezone(timedelta(hours=7))
start = datetime.now(tz) + timedelta(minutes=5)
end = start + timedelta(hours=2)

r = s.post('http://localhost:8000/api/bookings/', json={
    'vehicle_id': 'e8edbd26-5814-4137-9bfb-d93c58e22037',
    'parking_lot_id': 'bc1a3e4a-0b24-4510-892d-2d4b2b64c7b5',
    'floor_id': '30098e7d-fb8e-4e47-93a9-dd2b8ed8d28b',
    'zone_id': '86bf498a-7b08-4f4c-bc2d-3b0efca0c742',
    'slot_id': '<pick any available slot>',
    'package_type': 'hourly',
    'start_time': start.isoformat(),
    'end_time': end.isoformat(),
    'payment_type': 'cash'
})
print(json.dumps(r.json(), indent=2))
```

### Available Slots (Zone C)

To list available slots for Zone C:

```python
r = s.get('http://localhost:8000/api/parking/lots/bc1a3e4a-0b24-4510-892d-2d4b2b64c7b5/floors/30098e7d-fb8e-4e47-93a9-dd2b8ed8d28b/zones/86bf498a-7b08-4f4c-bc2d-3b0efca0c742/slots/')
slots = r.json()
available = [sl for sl in slots if sl.get('status') == 'available']
for sl in available[:5]:
    print(f"  {sl['label']} — {sl['id']}")
```

---

## Admin Account (for debugging)

| Field    | Value                 |
| -------- | --------------------- |
| Email    | `admin@parksmart.com` |
| Password | `admin1234@`          |

---

## API Quick Reference

| Endpoint                            | Method | Description                    |
| ----------------------------------- | ------ | ------------------------------ |
| `/api/auth/login/`                  | POST   | Login (returns session cookie) |
| `/api/bookings/`                    | GET    | List active bookings           |
| `/api/bookings/`                    | POST   | Create new booking             |
| `/api/ai/parking/esp32/check-in/`   | POST   | ESP32 gate check-in            |
| `/api/ai/parking/esp32/check-out/`  | POST   | ESP32 gate check-out           |
| `/api/ai/parking/detect-occupancy/` | POST   | AI slot detection              |
| `/api/parking/lots/`                | GET    | List parking lots              |

---

## Troubleshooting

### No bookings loading

- Check that Unity is hitting `http://localhost:8000/api/bookings/` with correct auth headers
- Verify cookies are stored after login

### WebSocket disconnection

- Verify realtime-service is running on port 8006
- Check `docker logs realtime-service-go` for errors
- Ensure WebSocket URL matches (`ws://` for local, `wss://` for HTTPS domain)

### AI detection fails

- AI service needs YOLO model + plate model to be loaded
- Check: `docker logs ai-service-fastapi`
- Verify model files exist in the container

### Gate doesn't open

- Check ESP32 endpoint response for error messages
- Verify booking status is `not_checked_in` (not already checked in)
- Check that `gate_id` format is correct

### Body consumption bug (ESP32 endpoint)

- Network requests may fail due to Starlette middleware reading the body stream
- **Workaround**: Use TestClient or ensure middleware doesn't consume `request.body()`
