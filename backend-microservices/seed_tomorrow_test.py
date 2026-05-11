#!/usr/bin/env python3
"""
ParkSmart — Seed comprehensive test data for April 18, 2026.

Creates diverse booking states at Vincom Center Parking for testing:
  - Group A: 7 vehicles currently parked (checked_in, slots occupied)
  - Group B: 5 reservations for tomorrow (not_checked_in, slots reserved)
  - Group C: 2 completed bookings from past days (checked_out)

Cleans up old Vincom bookings first, resets all slots to available,
then creates fresh data.

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_tomorrow_test.py
"""

import json
import os
import uuid
from datetime import datetime, timedelta

import pymysql

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "parksmartpass"),
    "database": os.environ.get("DB_NAME", "parksmartdb"),
    "charset": "utf8mb4",
}

NOW = datetime.now()
TOMORROW = NOW.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

# --- Vincom Center Parking (Unity lot) ---
VINCOM_LOT_ID = "3f54a675e64f4ea9a295ae8b068cc278"
VINCOM_LOT_NAME = "Vincom Center Parking"
FLOOR_ID = "418fa423a86d4f26a29f653bf522c933"
FLOOR_LEVEL = -1

ZONE_V1_ID = "dd657628ec4c477283e0f9b9a85e623d"  # Car, 72 slots
ZONE_V2_ID = "ff5416ec518c41439db3fac3e0974b0a"  # Motorbike, 20 slots
ZONE_G_ID = "77351b635c7d4cd987bded3660e67334"    # Car, 5 slots

ALL_ZONE_IDS = (ZONE_V1_ID, ZONE_V2_ID, ZONE_G_ID)

ZONES = {
    "V1": {"id": ZONE_V1_ID, "name": "Zone V1", "type": "Car"},
    "V2": {"id": ZONE_V2_ID, "name": "Zone V2", "type": "Motorbike"},
    "G":  {"id": ZONE_G_ID,  "name": "Zone G",  "type": "Car"},
}

# --- Existing users ---
USERS = {
    "chattest": {
        "id": "fac482571270449dbf81a92bf19e9a9c",
        "email": "chattest@parksmart.com",
    },
    "testdriver": {
        "id": "08fc117f5a5748a0ac995b2c44e6ae71",
        "email": "testdriver@parksmart.com",
    },
    "user1": {
        "id": "f8d32c7c9f324f24a7d9b05d9c4c5aec",
        "email": "user1@demo.com",
    },
    "user2": {
        "id": "b290001c2fb848beaefbba21ee6e624a",
        "email": "user2@demo.com",
    },
}

# --- Existing vehicles ---
VEHICLES = {
    "30A-111.11":  {"id": "2c73c138e3dd427fbcf3a80b4b4c847a", "type": "Car",       "owner": "testdriver"},
    "51G-888.88":  {"id": "3f8f40fc24aa41a286f711207d99d6dd", "type": "Car",       "owner": "chattest"},
    "51G-123.45":  {"id": "54eeff99927b40fba3ca8e75a79566a8", "type": "Car",       "owner": "user1"},
    "51H-678.90":  {"id": "2563317cf8b5441da31854003a866df4", "type": "Car",       "owner": "user2"},
    "29B1-234.56": {"id": "27b89f5dd61d433997ac0a7cef1e9d1d", "type": "Motorbike", "owner": "testdriver"},
    "59F1-567.89": {"id": "9c358d78aaca40e79d51165ee9ad78a3", "type": "Motorbike", "owner": "chattest"},
    "59F1-111.11": {"id": "0dab6cdd34254b438a8c93dbb6789bd3", "type": "Motorbike", "owner": "user1"},
}

# --- Hardcoded slot IDs (from DB) ---
SLOT_IDS = {
    "V1-01": "8c4932da815f4a2ba4bfbc39f527bf09",
    "V1-02": "b0722d92e5eb484088c69390ad3c1fa4",
    "V1-03": "2d5efeabaed54b5c8375110fbf41e845",
    "V1-04": "a9162c23824f412bb0fddf1dae8ad343",
    "V1-09": "5b6db9e4c96c4c538bce8ceeec7be264",
    "V1-10": "e790d50585e64259bdd1b593890365f1",
    "V1-11": "23b698d3a76e431cadcd599b053f1c19",
    "V1-12": "5eadd4bd9cfe40019fa957b2da6e3097",
    "V1-20": "362c7d7fc31e471681d2b5191af8ba9d",
    "V1-21": "c93bc8a2316a4458b1cbad095ef5ca6a",
    "G-01":  "f40f76a9bb14448b9e0fc9ab51945cc7",
    "G-02":  "295bf6a19b184f8680fde36789c574fe",
}


def get_connection() -> pymysql.Connection:
    return pymysql.connect(**DB_CONFIG)


def make_uuid() -> str:
    return uuid.uuid4().hex


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_slot_id(cur, zone_id: str, slot_code: str) -> str | None:
    """Look up slot ID by zone + code. Falls back to hardcoded map."""
    cur.execute(
        "SELECT id FROM car_slot WHERE zone_id=%s AND code=%s",
        (zone_id, slot_code),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    return SLOT_IDS.get(slot_code)


def make_qr(booking_id: str, user_id: str) -> str:
    return json.dumps({
        "booking_id": booking_id,
        "user_id": user_id,
        "timestamp": fmt(NOW),
    })


def step1_cleanup(conn: pymysql.Connection) -> None:
    """Delete all Vincom bookings and reset slots."""
    print("\n[1] Cleaning up old Vincom bookings...")
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM booking WHERE parking_lot_id = %s",
            (VINCOM_LOT_ID,),
        )
        deleted = cur.rowcount
        print(f"  Deleted {deleted} old bookings")
    conn.commit()


def step2_reset_slots(conn: pymysql.Connection) -> None:
    """Reset ALL Vincom slots to available."""
    print("\n[2] Resetting all Vincom slots to 'available'...")
    with conn.cursor() as cur:
        placeholders = ",".join(["%s"] * len(ALL_ZONE_IDS))
        cur.execute(
            f"UPDATE car_slot SET status='available' WHERE zone_id IN ({placeholders})",
            ALL_ZONE_IDS,
        )
        updated = cur.rowcount
        print(f"  Reset {updated} slots to 'available'")
    conn.commit()


def insert_booking(
    cur,
    user_key: str,
    plate: str,
    slot_code: str,
    zone_key: str,
    start_time: datetime,
    end_time: datetime,
    check_in_status: str,
    checked_in_at: datetime | None,
    checked_out_at: datetime | None,
    payment_status: str,
    price: int,
) -> str:
    """Insert a single booking row. Returns booking ID."""
    user = USERS[user_key]
    vehicle = VEHICLES[plate]
    zone = ZONES[zone_key]
    bid = make_uuid()

    slot_id = None
    if slot_code in SLOT_IDS:
        slot_id = SLOT_IDS[slot_code]
    else:
        cur.execute(
            "SELECT id FROM car_slot WHERE zone_id=%s AND code=%s",
            (zone["id"], slot_code),
        )
        row = cur.fetchone()
        slot_id = row[0] if row else make_uuid()

    qr = make_qr(bid, user["id"])

    cur.execute(
        """INSERT INTO booking
            (id, user_id, user_email,
             vehicle_id, vehicle_license_plate, vehicle_type,
             parking_lot_id, parking_lot_name,
             floor_id, floor_level,
             zone_id, zone_name,
             slot_id, slot_code,
             package_type, start_time, end_time,
             payment_method, payment_status, price,
             check_in_status, checked_in_at, checked_out_at,
             qr_code_data, late_fee_applied,
             created_at, updated_at)
           VALUES (%s,%s,%s, %s,%s,%s, %s,%s, %s,%s, %s,%s, %s,%s,
                   %s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s, %s,%s)""",
        (
            bid,
            user["id"],
            user["email"],
            vehicle["id"],
            plate,
            vehicle["type"],
            VINCOM_LOT_ID,
            VINCOM_LOT_NAME,
            FLOOR_ID,
            FLOOR_LEVEL,
            zone["id"],
            zone["name"],
            slot_id,
            slot_code,
            "hourly",
            fmt(start_time),
            fmt(end_time),
            "cash" if payment_status == "pending" else "online",
            payment_status,
            price,
            check_in_status,
            fmt(checked_in_at) if checked_in_at else None,
            fmt(checked_out_at) if checked_out_at else None,
            qr,
            False,
            fmt(NOW),
            fmt(NOW),
        ),
    )
    return bid


def step3_currently_parked(conn: pymysql.Connection) -> list[str]:
    """Group A: 7 vehicles currently parked (checked_in, slots occupied)."""
    print("\n[3] Creating currently parked bookings (checked_in)...")

    specs = [
        # Car slots in Zone V1
        {"slot": "V1-01", "zone": "V1", "user": "testdriver", "plate": "30A-111.11",  "ago_min": 120, "price": 20000},
        {"slot": "V1-02", "zone": "V1", "user": "chattest",   "plate": "51G-888.88",  "ago_min": 60,  "price": 20000},
        {"slot": "V1-03", "zone": "V1", "user": "user1",      "plate": "51G-123.45",  "ago_min": 45,  "price": 20000},
        {"slot": "V1-04", "zone": "V1", "user": "user2",      "plate": "51H-678.90",  "ago_min": 30,  "price": 20000},
        # Motorbike slots in Zone V2
        {"slot": "V2-01", "zone": "V2", "user": "testdriver", "plate": "29B1-234.56", "ago_min": 90,  "price": 5000},
        {"slot": "V2-02", "zone": "V2", "user": "chattest",   "plate": "59F1-567.89", "ago_min": 50,  "price": 5000},
        {"slot": "V2-03", "zone": "V2", "user": "user1",      "plate": "59F1-111.11", "ago_min": 20,  "price": 5000},
    ]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for s in specs:
            checked_in_at = NOW - timedelta(minutes=s["ago_min"])
            start_time = checked_in_at - timedelta(minutes=5)
            end_time = checked_in_at + timedelta(hours=4)

            bid = insert_booking(
                cur,
                user_key=s["user"],
                plate=s["plate"],
                slot_code=s["slot"],
                zone_key=s["zone"],
                start_time=start_time,
                end_time=end_time,
                check_in_status="checked_in",
                checked_in_at=checked_in_at,
                checked_out_at=None,
                payment_status="pending",
                price=s["price"],
            )
            booking_ids.append(bid)

            # Mark slot as occupied
            zone = ZONES[s["zone"]]
            cur.execute(
                "UPDATE car_slot SET status='occupied' WHERE zone_id=%s AND code=%s",
                (zone["id"], s["slot"]),
            )
            print(f"  OK  {s['slot']:6s} ← {s['plate']:13s} ({s['user']:12s}) parked {s['ago_min']}min ago")

    conn.commit()
    return booking_ids


def step4_tomorrow_reservations(conn: pymysql.Connection) -> list[str]:
    """Group B: 5 reservations for tomorrow (not_checked_in, slots reserved)."""
    print("\n[4] Creating tomorrow reservations (not_checked_in)...")

    specs = [
        {"slot": "V1-09", "zone": "V1", "user": "chattest",   "plate": "51G-888.88",  "hour": 8,  "dur": 4, "price": 80000},
        {"slot": "V1-10", "zone": "V1", "user": "testdriver", "plate": "30A-111.11",  "hour": 9,  "dur": 4, "price": 80000},
        {"slot": "V1-11", "zone": "V1", "user": "user1",      "plate": "51G-123.45",  "hour": 10, "dur": 4, "price": 80000},
        {"slot": "V1-12", "zone": "V1", "user": "user2",      "plate": "51H-678.90",  "hour": 7,  "dur": 4, "price": 80000},
        {"slot": "G-02",  "zone": "G",  "user": "chattest",   "plate": "51G-888.88",  "hour": 14, "dur": 3, "price": 60000},
    ]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for s in specs:
            start_time = TOMORROW.replace(hour=s["hour"])
            end_time = start_time + timedelta(hours=s["dur"])

            bid = insert_booking(
                cur,
                user_key=s["user"],
                plate=s["plate"],
                slot_code=s["slot"],
                zone_key=s["zone"],
                start_time=start_time,
                end_time=end_time,
                check_in_status="not_checked_in",
                checked_in_at=None,
                checked_out_at=None,
                payment_status="pending",
                price=s["price"],
            )
            booking_ids.append(bid)

            # Mark slot as reserved
            zone = ZONES[s["zone"]]
            cur.execute(
                "UPDATE car_slot SET status='reserved' WHERE zone_id=%s AND code=%s",
                (zone["id"], s["slot"]),
            )
            st = start_time.strftime("%H:%M")
            et = end_time.strftime("%H:%M")
            print(f"  OK  {s['slot']:6s} ← {s['plate']:13s} ({s['user']:12s}) tomorrow {st}-{et}")

    conn.commit()
    return booking_ids


def step5_past_completed(conn: pymysql.Connection) -> list[str]:
    """Group C: 2 completed bookings from past days (checked_out)."""
    print("\n[5] Creating past completed bookings (checked_out)...")

    specs = [
        {
            "slot": "V1-20", "zone": "V1",
            "user": "chattest", "plate": "51G-888.88",
            "days_ago": 1, "hour": 10, "dur": 3, "price": 60000,
        },
        {
            "slot": "V1-21", "zone": "V1",
            "user": "testdriver", "plate": "30A-111.11",
            "days_ago": 2, "hour": 14, "dur": 2, "price": 40000,
        },
    ]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for s in specs:
            day = NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=s["days_ago"])
            start_time = day.replace(hour=s["hour"])
            end_time = start_time + timedelta(hours=s["dur"])
            checked_in_at = start_time + timedelta(minutes=3)
            checked_out_at = end_time - timedelta(minutes=10)

            bid = insert_booking(
                cur,
                user_key=s["user"],
                plate=s["plate"],
                slot_code=s["slot"],
                zone_key=s["zone"],
                start_time=start_time,
                end_time=end_time,
                check_in_status="checked_out",
                checked_in_at=checked_in_at,
                checked_out_at=checked_out_at,
                payment_status="paid",
                price=s["price"],
            )
            booking_ids.append(bid)

            day_label = "yesterday" if s["days_ago"] == 1 else f"{s['days_ago']} days ago"
            print(f"  OK  {s['slot']:6s} ← {s['plate']:13s} ({s['user']:12s}) {day_label}")

    conn.commit()
    return booking_ids


def print_summary(conn: pymysql.Connection) -> None:
    print("\n" + "=" * 70)
    print("SUMMARY — Vincom Center Parking Test Data")
    print("=" * 70)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT check_in_status, COUNT(*) FROM booking "
            "WHERE parking_lot_id=%s GROUP BY check_in_status",
            (VINCOM_LOT_ID,),
        )
        rows = cur.fetchall()
        print("\n  Booking counts by status:")
        for status, count in rows:
            print(f"    {status:20s}: {count}")

        cur.execute(
            "SELECT status, COUNT(*) FROM car_slot "
            "WHERE zone_id IN (%s,%s,%s) GROUP BY status",
            ALL_ZONE_IDS,
        )
        rows = cur.fetchall()
        print("\n  Slot counts by status:")
        for status, count in rows:
            print(f"    {status:20s}: {count}")

        print("\n  Currently parked (checked_in):")
        cur.execute(
            "SELECT slot_code, vehicle_license_plate, user_email, checked_in_at "
            "FROM booking WHERE parking_lot_id=%s AND check_in_status='checked_in' "
            "ORDER BY slot_code",
            (VINCOM_LOT_ID,),
        )
        for row in cur.fetchall():
            print(f"    {row[0]:6s}  {row[1]:13s}  {row[2]:30s}  since {row[3]}")

        print("\n  Tomorrow reservations (not_checked_in):")
        cur.execute(
            "SELECT slot_code, vehicle_license_plate, user_email, start_time, end_time "
            "FROM booking WHERE parking_lot_id=%s AND check_in_status='not_checked_in' "
            "ORDER BY start_time",
            (VINCOM_LOT_ID,),
        )
        for row in cur.fetchall():
            print(f"    {row[0]:6s}  {row[1]:13s}  {row[2]:30s}  {row[3]} → {row[4]}")

        print("\n  Past completed (checked_out):")
        cur.execute(
            "SELECT slot_code, vehicle_license_plate, user_email, checked_in_at, checked_out_at "
            "FROM booking WHERE parking_lot_id=%s AND check_in_status='checked_out' "
            "ORDER BY checked_in_at DESC",
            (VINCOM_LOT_ID,),
        )
        for row in cur.fetchall():
            print(f"    {row[0]:6s}  {row[1]:13s}  {row[2]:30s}  {row[3]} → {row[4]}")

    print("\n" + "=" * 70)
    print("Test credentials:")
    print("  chattest@parksmart.com   / Test@1234")
    print("  testdriver@parksmart.com / Test@1234")
    print("  user1@demo.com           / Test@1234")
    print("  user2@demo.com           / Test@1234")
    print(f"\nParking lot: {VINCOM_LOT_NAME} (id={VINCOM_LOT_ID})")
    print(f"Tomorrow date: {TOMORROW.strftime('%Y-%m-%d')}")
    print("=" * 70)


def main() -> None:
    print("ParkSmart — Comprehensive Test Data Seeder")
    print(f"Target: Vincom Center Parking")
    print(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"Now: {fmt(NOW)}")
    print(f"Tomorrow: {TOMORROW.strftime('%Y-%m-%d')}")
    print("-" * 70)

    try:
        conn = get_connection()
    except Exception as e:
        print(f"ERROR: Cannot connect to DB: {e}")
        raise SystemExit(1)

    try:
        step1_cleanup(conn)
        step2_reset_slots(conn)

        parked_ids = step3_currently_parked(conn)
        reserved_ids = step4_tomorrow_reservations(conn)
        completed_ids = step5_past_completed(conn)

        total = len(parked_ids) + len(reserved_ids) + len(completed_ids)
        print(f"\n  Total bookings created: {total}")
        print(f"    Parked (checked_in):        {len(parked_ids)}")
        print(f"    Reserved (not_checked_in):   {len(reserved_ids)}")
        print(f"    Completed (checked_out):     {len(completed_ids)}")

        print_summary(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
