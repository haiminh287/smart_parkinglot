"""Tạo 1 booking NOW → +3h cho Unity simulator check-in.

Dùng: python create_unity_checkin_booking.py

Output:
- booking_id (UUID)
- qr_data JSON với {booking_id, user_id}
- Lưu vào booking_for_unity.json cho Unity đọc
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymysql

DB = dict(host="127.0.0.1", port=3307, user="parksmartuser",
          password="parksmartpass", database="parksmartdb", charset="utf8mb4")

# === Unity seed defaults ===
USER_ID = "fac482571270449dbf81a92bf19e9a9c"        # chattest@parksmart.com
USER_EMAIL = "chattest@parksmart.com"
VEHICLE_ID = "3f8f40fc24aa41a286f711207d99d6dd"     # 51G-888.88 Toyota
VEHICLE_PLATE = "51G-888.88"
VEHICLE_TYPE = "Car"
PARKING_LOT_ID = "3f54a675e64f4ea9a295ae8b068cc278"  # Vincom Center Parking (Unity default)
PARKING_LOT_NAME = "Vincom Center Parking"
FLOOR_ID = "418fa423a86d4f26a29f653bf522c933"         # Floor level -1
FLOOR_LEVEL = -1
ZONE_ID = "77351b635c7d4cd987bded3660e67334"          # Zone G (Car)
ZONE_NAME = "Zone G"
SLOT_ID = "f40f76a9bb14448b9e0fc9ab51945cc7"          # G-01 available
SLOT_CODE = "G-01"

def main():
    # Server (booking-service) so sánh start_time ở UTC.
    # Dùng UTC ở đây để tránh lệch timezone 7h.
    now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    start = now - timedelta(minutes=30)  # cho phép check-in ngay
    end = now + timedelta(hours=3)
    booking_id = uuid.uuid4().hex
    qr_payload = {"booking_id": booking_id, "user_id": USER_ID}
    qr_data = json.dumps(qr_payload, separators=(",", ":"))

    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            # Insert booking — denormalized schema after S2-IMP-1
            cur.execute(
                """
                INSERT INTO booking (
                    id, user_id, user_email,
                    vehicle_id, vehicle_license_plate, vehicle_type,
                    parking_lot_id, parking_lot_name,
                    floor_id, floor_level,
                    zone_id, zone_name,
                    slot_id, slot_code,
                    package_type, start_time, end_time,
                    payment_method, payment_status, price,
                    check_in_status, qr_code_data,
                    hourly_start, hourly_end, late_fee_applied,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    'hourly', %s, %s,
                    'on_exit', 'pending', 45000,
                    'not_checked_in', %s,
                    %s, %s, 0,
                    %s, %s
                )
                """,
                (
                    booking_id, USER_ID, USER_EMAIL,
                    VEHICLE_ID, VEHICLE_PLATE, VEHICLE_TYPE,
                    PARKING_LOT_ID, PARKING_LOT_NAME,
                    FLOOR_ID, FLOOR_LEVEL,
                    ZONE_ID, ZONE_NAME,
                    SLOT_ID, SLOT_CODE,
                    start, end,
                    qr_data,
                    start, end,
                    now, now,
                ),
            )
            # Reserve slot
            cur.execute(
                "UPDATE car_slot SET status='reserved' WHERE id=%s AND status='available'",
                (SLOT_ID,),
            )
        conn.commit()
    finally:
        conn.close()

    out = {
        "booking_id": booking_id,
        "user_id": USER_ID,
        "license_plate": VEHICLE_PLATE,
        "slot_code": SLOT_CODE,
        "zone_name": ZONE_NAME,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "qr_data": qr_data,
    }
    outfile = Path(__file__).parent.parent / "booking_for_unity.json"
    outfile.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print("=" * 60)
    print(f"✅ Booking CREATED — ready to check-in")
    print("=" * 60)
    print(f"  booking_id : {booking_id}")
    print(f"  user_id    : {USER_ID}")
    print(f"  plate      : {VEHICLE_PLATE}")
    print(f"  slot       : {SLOT_CODE}  ({ZONE_NAME})")
    print(f"  window     : {start.strftime('%H:%M')}  →  {end.strftime('%H:%M')}")
    print(f"  qr_data    : {qr_data}")
    print(f"  saved to   : {outfile}")
    print("=" * 60)
    print("\nTest check-in (curl):")
    print(f"""  curl -X POST http://localhost:8009/ai/parking/esp32/check-in/ \\
    -H "X-Gateway-Secret: $GATEWAY_SECRET" \\
    -H "X-Device-Token: $ESP32_DEVICE_TOKEN" \\
    -d '{{"gate_id":"GATE-IN-01"}}'""")


if __name__ == "__main__":
    main()
