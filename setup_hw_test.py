"""Setup vehicle + booking for plate 51A-224.56 hardware test."""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


BASE_HEADERS = {
    "Content-Type": "application/json",
    "X-Gateway-Secret": "gateway-internal-secret-key",
    "X-User-ID": "ecab8dcb-d320-4d63-8283-98094e3ac486",
}
USER_ID = "ecab8dcb-d320-4d63-8283-98094e3ac486"


def _request(url: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in BASE_HEADERS.items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        print(f"  HTTP {e.code}: {txt}")
        return {"error": e.code, "body": txt}


def list_vehicles() -> list:
    print("=== Listing vehicles ===")
    data = _request("http://localhost:8004/vehicles/")
    vehicles = data.get("results", data if isinstance(data, list) else [])
    for v in vehicles:
        print(f"  {v['id']} | {v['licensePlate']} | {v['name']}")
    return vehicles


def create_vehicle_db(plate: str, user_id_hex: str) -> str | None:
    """Create vehicle directly in MySQL (vehicle-service not running locally)."""
    import mysql.connector
    import uuid
    print(f"\n=== Creating vehicle plate={plate} in DB ===")
    conn = mysql.connector.connect(
        host="localhost", port=3307, user="root",
        password="parksmartpass", database="parksmartdb",
    )
    cur = conn.cursor()
    # Check existing
    cur.execute("SELECT id FROM vehicle WHERE license_plate=%s", (plate,))
    row = cur.fetchone()
    if row:
        vid_hex = row[0]
        # Ensure it belongs to our test user
        cur.execute(
            "UPDATE vehicle SET user_id=%s WHERE id=%s", (user_id_hex, vid_hex),
        )
        conn.commit()
        print(f"  Vehicle exists, updated ownership: {vid_hex}")
    else:
        vid_hex = uuid.uuid4().hex
        now = datetime.now()
        cur.execute(
            "INSERT INTO vehicle (id,user_id,license_plate,vehicle_type,"
            "brand,model,color,is_default,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (vid_hex, user_id_hex, plate, "Car", "", "", "", 0, now, now),
        )
        conn.commit()
        print(f"  Created vehicle: {vid_hex}")
    conn.close()
    # Return UUID with dashes
    return f"{vid_hex[:8]}-{vid_hex[8:12]}-{vid_hex[12:16]}-{vid_hex[16:20]}-{vid_hex[20:]}"


def create_booking(vehicle_id: str) -> dict | None:
    print(f"\n=== Creating booking for vehicle {vehicle_id} ===")
    tz = timezone(timedelta(hours=7))
    now = datetime.now(tz)
    data = _request("http://localhost:8002/bookings/", "POST", {
        "vehicleId": vehicle_id,
        "slotId": "8731a645-13f6-457e-b66a-07a92f9c437f",
        "parkingLotId": "3f54a675-e64f-4ea9-a295-ae8b068cc278",
        "zoneId": "33617983-30b7-4d44-a21d-ce6d1cbea733",
        "floorId": "3ef3002a-cc2c-4e56-a64f-ba99ec708a2b",
        "packageType": "hourly",
        "paymentType": "on_exit",
        "startTime": now.isoformat(),
        "endTime": (now + timedelta(hours=2)).isoformat(),
    })
    if "error" in data:
        print(f"  Failed: {data}")
        return None
    booking = data.get("booking", data)
    bid = booking.get("id", "?")
    status = booking.get("checkInStatus", "?")
    slot = booking.get("carSlot", {}).get("code", "?")
    qr = booking.get("qrCodeData", "")
    print(f"  Booking ID:  {bid}")
    print(f"  Status:      {status}")
    print(f"  Slot:        {slot}")
    print(f"  Plate:       {booking.get('vehicle', {}).get('licensePlate', '?')}")
    print(f"  QR Data:     {qr}")
    return booking


def generate_qr(booking_id: str) -> None:
    import qrcode
    import os
    data = json.dumps({
        "booking_id": booking_id,
        "user_id": USER_ID,
    })
    img = qrcode.make(data)
    path = os.path.join(
        r"C:\Users\MINH\Documents\Zalo_Received_Files\Project_Main",
        "qr_checkin.png",
    )
    img.save(path)
    print(f"\n✅ QR code saved: {path}")
    print(f"   Data: {data}")


if __name__ == "__main__":
    # Step 1: Create/ensure vehicle in DB
    plate = "51A-224.56"
    user_id_hex = USER_ID.replace("-", "")
    vehicle_id = create_vehicle_db(plate, user_id_hex)
    if not vehicle_id:
        print("FAILED to create vehicle!")
        exit(1)
    print(f"  Vehicle ID (UUID): {vehicle_id}")

    # Step 3: Create booking
    booking = create_booking(vehicle_id)
    if not booking:
        print("FAILED to create booking!")
        exit(1)

    # Step 4: Generate QR code
    generate_qr(booking["id"])

    print("\n" + "=" * 60)
    print("🎯 READY FOR HARDWARE TEST!")
    print(f"   Booking ID: {booking['id']}")
    print(f"   Plate:      {plate}")
    print(f"   Slot:       {booking.get('carSlot', {}).get('code', '?')}")
    print("=" * 60)
    print("1. Mở file qr_checkin.png trên điện thoại/màn hình")
    print("2. Mở DroidCam trên điện thoại")
    print("3. Nhấn CHECK-IN trên ESP32")
    print("4. Đưa QR code vào trước camera DroidCam")
