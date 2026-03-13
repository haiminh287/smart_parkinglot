"""Create a new booking for hardware testing."""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


def create_booking() -> None:
    """Create a new booking with slot B-13 for hardware check-in/out testing."""
    url = "http://localhost:8002/bookings/"
    tz = timezone(timedelta(hours=7))
    now = datetime.now(tz)
    start = now.isoformat()
    end = (now + timedelta(hours=2)).isoformat()

    body = json.dumps({
        "vehicleId": "c27635bb-8a2a-4e7a-a7cd-eedf6dacae3a",
        "slotId": "0a8b0e72-09de-4b13-acbc-4a8727d8dee2",
        "parkingLotId": "3f54a675-e64f-4ea9-a295-ae8b068cc278",
        "zoneId": "33617983-30b7-4d44-a21d-ce6d1cbea733",
        "floorId": "3ef3002a-cc2c-4e56-a64f-ba99ec708a2b",
        "packageType": "hourly",
        "paymentType": "on_exit",
        "startTime": start,
        "endTime": end,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Gateway-Secret", "gateway-internal-secret-key")
    req.add_header("X-User-ID", "ecab8dcb-d320-4d63-8283-98094e3ac486")

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        print(f"✅ BOOKING CREATED!")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        print(f"❌ HTTP Error: {e.code}")
        print(body_text)


if __name__ == "__main__":
    create_booking()
