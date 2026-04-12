#!/usr/bin/env python3
"""
ParkSmart — Seed comprehensive test data for admin@example.com.

Creates:
  - Profile update (first_name, last_name, phone, address)
  - 2 vehicles (Car + Motorbike)
  - 6 bookings in various states (completed, active, upcoming, cancelled, no_show, pending_payment)
  - 3 payment records for completed bookings
  - Notifications

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_admin_test_data.py
"""

import base64
import hashlib
import json
import os
import secrets
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

# Known IDs from DB inspection
ADMIN_USER_ID = "64ed02950d1842c19e52dd787b8bd847"
ADMIN_EMAIL = "admin@example.com"

PARKING_LOTS = {
    "vincom": {
        "id": "3f54a675e64f4ea9a295ae8b068cc278",
        "name": "Vincom Center Parking",
        "floor_id": "418fa423a86d4f26a29f653bf522c933",
        "floor_level": -1,
        "floor_name": "B1",
    },
    "parksmart": {
        "id": "bc1a3e4a0b244510892d2d4b2b64c7b5",
        "name": "ParkSmart Tower",
        "floor_id": "3ef3002acc2c4e56a64fba99ec708a2b",
        "floor_level": 1,
        "floor_name": "Tang 1",
    },
}

ZONES = {
    "V1": {"id": "dd657628ec4c477283e0f9b9a85e623d", "name": "Zone V1", "type": "Car"},
    "V2": {"id": "ff5416ec518c41439db3fac3e0974b0a", "name": "Zone V2", "type": "Motorbike"},
    "A": {"id": "9bae0162f2a24faaa10791ba3fcd5186", "name": "Zone A", "type": "Car"},
    "B": {"id": "3361798330b74d44a21dce6d1cbea733", "name": "Zone B", "type": "Car"},
}

SLOTS = {
    "V1-39": {"id": "031ca239436748f9a6b1a65261375b95", "zone": "V1"},
    "V2-32": {"id": "02518136d3804305b3efff4621bc947d", "zone": "V2"},
    "A-07": {"id": "03e53b7f8a3d47c5a7b26ba12df94a3e", "zone": "A"},
    "A-10": {"id": "03e8595cdfc44adaa38efccc23b875ec", "zone": "A"},
    "B-01": {"id": None, "zone": "B"},  # will query
}

NOW = datetime.utcnow()


def get_connection() -> pymysql.Connection:
    return pymysql.connect(**DB_CONFIG)


def make_uuid() -> str:
    return uuid.uuid4().hex


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def update_admin_profile(conn: pymysql.Connection) -> None:
    print("\n[1] Updating admin profile...")
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE users_user SET
                first_name = %s,
                last_name  = %s,
                phone      = %s,
                address    = %s
            WHERE id = %s""",
            ("Admin", "ParkSmart", "0912345678", "123 Nguyen Hue, Q1, TP.HCM", ADMIN_USER_ID),
        )
    conn.commit()
    print("  OK - first_name=Admin, last_name=ParkSmart, phone=0912345678")


def seed_vehicles(conn: pymysql.Connection) -> dict[str, str]:
    """Returns {license_plate: vehicle_id}."""
    print("\n[2] Seeding vehicles...")
    vehicles_data = [
        {"plate": "29A-12345", "type": "Car",       "brand": "Toyota",  "model": "Camry 2.5Q",    "color": "White",  "default": True},
        {"plate": "29B1-56789","type": "Motorbike",  "brand": "Honda",   "model": "Vision 2023",   "color": "Black",  "default": False},
    ]
    result: dict[str, str] = {}
    with conn.cursor() as cur:
        for v in vehicles_data:
            cur.execute("SELECT id FROM vehicle WHERE license_plate = %s", (v["plate"],))
            row = cur.fetchone()
            if row:
                vid = row[0]
                print(f"  SKIP {v['plate']} (already exists, id={vid})")
            else:
                vid = make_uuid()
                cur.execute(
                    """INSERT INTO vehicle
                        (id, user_id, license_plate, vehicle_type, brand, model, color, is_default, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (vid, ADMIN_USER_ID, v["plate"], v["type"], v["brand"],
                     v["model"], v["color"], v["default"], fmt(NOW), fmt(NOW)),
                )
                print(f"  OK - {v['plate']} ({v['type']}) id={vid}")
            result[v["plate"]] = vid
    conn.commit()
    return result


def get_available_slot(conn: pymysql.Connection, zone_id: str, exclude_ids: list[str]) -> tuple[str, str] | None:
    """Returns (slot_id, slot_code) or None."""
    with conn.cursor() as cur:
        placeholders = ",".join(["%s"] * len(exclude_ids)) if exclude_ids else "'__none__'"
        query = f"SELECT id, code FROM car_slot WHERE zone_id = %s AND status = 'available'"
        params = [zone_id]
        if exclude_ids:
            query += f" AND id NOT IN ({','.join(['%s']*len(exclude_ids))})"
            params.extend(exclude_ids)
        query += " LIMIT 1"
        cur.execute(query, params)
        row = cur.fetchone()
        return (row[0], row[1]) if row else None


def seed_bookings(conn: pymysql.Connection, vehicles: dict[str, str]) -> list[str]:
    print("\n[3] Seeding bookings...")

    car_plate   = "29A-12345"
    moto_plate  = "29B1-56789"
    car_id      = vehicles.get(car_plate, make_uuid())
    moto_id     = vehicles.get(moto_plate, make_uuid())

    used_slots: list[str] = []
    # Pre-grab slots
    s_v1_39  = ("031ca239436748f9a6b1a65261375b95", "V1-39")
    s_v2_32  = ("02518136d3804305b3efff4621bc947d", "V2-32")
    s_a07    = ("03e53b7f8a3d47c5a7b26ba12df94a3e", "A-07")
    s_a10    = ("03e8595cdfc44adaa38efccc23b875ec", "A-10")

    # Dynamic slot for upcoming booking
    s_b_upcoming = get_available_slot(conn, ZONES["B"]["id"], [s_a07[0], s_a10[0]])

    lot_vincom    = PARKING_LOTS["vincom"]
    lot_parksmart = PARKING_LOTS["parksmart"]

    bookings = [
        # 1) Completed + paid + checked_out — 7 days ago, 2h duration
        {
            "id": make_uuid(),
            "lot": lot_vincom, "zone": ZONES["V1"], "slot": s_v1_39,
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW - timedelta(days=7, hours=4),
            "end":   NOW - timedelta(days=7, hours=2),
            "package": "hourly", "payment_method": "cash",
            "payment_status": "completed",
            "check_in_status": "checked_out",
            "checked_in_at":  NOW - timedelta(days=7, hours=4),
            "checked_out_at": NOW - timedelta(days=7, hours=2),
            "price": 30000,
            "desc": "Completed / cash / checked_out",
        },
        # 2) Completed + paid (online) + checked_out — 3 days ago, 3h
        {
            "id": make_uuid(),
            "lot": lot_parksmart, "zone": ZONES["A"], "slot": s_a07,
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW - timedelta(days=3, hours=5),
            "end":   NOW - timedelta(days=3, hours=2),
            "package": "hourly", "payment_method": "online",
            "payment_status": "completed",
            "check_in_status": "checked_out",
            "checked_in_at":  NOW - timedelta(days=3, hours=5),
            "checked_out_at": NOW - timedelta(days=3, hours=2),
            "price": 45000,
            "desc": "Completed / online(momo) / checked_out",
        },
        # 3) Active — checked_in right now, ends in 2h
        {
            "id": make_uuid(),
            "lot": lot_parksmart, "zone": ZONES["A"], "slot": s_a10,
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW - timedelta(hours=1),
            "end":   NOW + timedelta(hours=2),
            "package": "hourly", "payment_method": "on_exit",
            "payment_status": "pending",
            "check_in_status": "checked_in",
            "checked_in_at":  NOW - timedelta(hours=1),
            "checked_out_at": None,
            "price": 45000,
            "desc": "Active / on_exit / checked_in",
        },
        # 4) Upcoming — booked for tomorrow, not checked in
        {
            "id": make_uuid(),
            "lot": lot_vincom, "zone": ZONES["V1"],
            "slot": s_b_upcoming if s_b_upcoming else s_v1_39,
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW + timedelta(days=1, hours=9),
            "end":   NOW + timedelta(days=1, hours=11),
            "package": "hourly", "payment_method": "online",
            "payment_status": "completed",
            "check_in_status": "not_checked_in",
            "checked_in_at": None, "checked_out_at": None,
            "price": 30000,
            "desc": "Upcoming / online / not_checked_in",
        },
        # 5) Cancelled — 2 days ago
        {
            "id": make_uuid(),
            "lot": lot_parksmart, "zone": ZONES["B"], "slot": s_a07,
            "vehicle_id": moto_id, "plate": moto_plate, "vtype": "Motorbike",
            "start": NOW - timedelta(days=2, hours=14),
            "end":   NOW - timedelta(days=2, hours=12),
            "package": "hourly", "payment_method": "cash",
            "payment_status": "refunded",
            "check_in_status": "cancelled",
            "checked_in_at": None, "checked_out_at": None,
            "price": 10000,
            "desc": "Cancelled / refunded",
        },
        # 6) No-show — 5 days ago
        {
            "id": make_uuid(),
            "lot": lot_vincom, "zone": ZONES["V2"], "slot": s_v2_32,
            "vehicle_id": moto_id, "plate": moto_plate, "vtype": "Motorbike",
            "start": NOW - timedelta(days=5, hours=10),
            "end":   NOW - timedelta(days=5, hours=8),
            "package": "hourly", "payment_method": "online",
            "payment_status": "failed",
            "check_in_status": "no_show",
            "checked_in_at": None, "checked_out_at": None,
            "price": 20000,
            "desc": "No-show / payment failed",
        },
    ]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for b in bookings:
            cur.execute("SELECT id FROM booking WHERE user_id=%s AND slot_id=%s AND start_time=%s",
                        (ADMIN_USER_ID, b["slot"][0], fmt(b["start"])))
            if cur.fetchone():
                print(f"  SKIP {b['desc']} (already exists)")
                continue

            lot    = b["lot"]
            zone   = b["zone"]
            slot   = b["slot"]
            bid    = b["id"]

            qr_data = json.dumps({
                "booking_id": bid,
                "user_id": ADMIN_USER_ID,
                "lot": lot["name"],
                "slot": slot[1],
            })

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
                    bid, ADMIN_USER_ID, ADMIN_EMAIL,
                    b["vehicle_id"], b["plate"], b["vtype"],
                    lot["id"], lot["name"],
                    lot["floor_id"], lot["floor_level"],
                    zone["id"], zone["name"],
                    slot[0], slot[1],
                    b["package"], fmt(b["start"]), fmt(b["end"]),
                    b["payment_method"], b["payment_status"], b["price"],
                    b["check_in_status"],
                    fmt(b["checked_in_at"]) if b["checked_in_at"] else None,
                    fmt(b["checked_out_at"]) if b["checked_out_at"] else None,
                    qr_data, False,
                    fmt(b["start"]), fmt(NOW),
                ),
            )
            booking_ids.append(bid)
            print(f"  OK - {b['desc']} | slot={slot[1]} | price={b['price']}")

    conn.commit()
    # Mark active booking's slot as occupied
    with conn.cursor() as cur:
        cur.execute("UPDATE car_slot SET status='occupied' WHERE id=%s", (s_a10[0],))
    conn.commit()
    print(f"  OK - Marked slot A-10 as occupied (active booking)")
    return booking_ids


def seed_payments(conn: pymysql.Connection, booking_ids: list[str]) -> None:
    print("\n[4] Seeding payments...")
    if not booking_ids:
        print("  SKIP - no booking IDs")
        return

    # Seed payments for first 2 (completed) + 1 pending
    payment_data = [
        {"booking_idx": 0, "method": "cash",  "amount": 30000, "status": "completed", "tx_suffix": "CASH001"},
        {"booking_idx": 1, "method": "momo",  "amount": 45000, "status": "completed", "tx_suffix": "MOMO002"},
        {"booking_idx": 2, "method": "cash",  "amount": 45000, "status": "pending",   "tx_suffix": "CASH003"},
    ]

    with conn.cursor() as cur:
        for p in payment_data:
            idx = p["booking_idx"]
            if idx >= len(booking_ids):
                continue
            bid = booking_ids[idx]
            pid = make_uuid()
            tx_id = f"PS-{ADMIN_USER_ID[:8].upper()}-{p['tx_suffix']}"
            completed_at = fmt(NOW - timedelta(days=7 - idx)) if p["status"] == "completed" else None
            cur.execute(
                """INSERT INTO payments_payment
                    (id, booking_id, user_id, payment_method, amount,
                     transaction_id, status, initiated_at, completed_at,
                     created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE id=id""",
                (
                    pid, bid, ADMIN_USER_ID, p["method"], p["amount"],
                    tx_id, p["status"],
                    fmt(NOW - timedelta(days=8 - idx)),
                    completed_at,
                    fmt(NOW), fmt(NOW),
                ),
            )
            print(f"  OK - {p['method']} {p['amount']}d tx={tx_id} status={p['status']}")
    conn.commit()


def seed_notifications(conn: pymysql.Connection) -> None:
    print("\n[5] Seeding notifications...")
    notifs = [
        {
            "type": "booking",
            "title": "Dat cho thanh cong",
            "message": "Booking #V1-39 tai Vincom Center da duoc xac nhan. Bat dau: 7 ngay truoc.",
            "is_read": True,
            "created_at": NOW - timedelta(days=7),
        },
        {
            "type": "payment",
            "title": "Thanh toan thanh cong",
            "message": "Thanh toan 45.000d cho booking tai ParkSmart Tower da hoan tat qua Momo.",
            "is_read": True,
            "created_at": NOW - timedelta(days=3),
        },
        {
            "type": "booking",
            "title": "Nhac nho check-in",
            "message": "Ban co mot booking sap toi tai Vincom Center vao ngay mai luc 09:00.",
            "is_read": False,
            "created_at": NOW - timedelta(hours=2),
        },
        {
            "type": "system",
            "title": "Cap nhat he thong",
            "message": "ParkSmart da cap nhat tinh nang tim duong thong minh Dijkstra v2. Thu ngay!",
            "is_read": False,
            "created_at": NOW - timedelta(hours=1),
        },
    ]

    with conn.cursor() as cur:
        ts_fmt = "%Y-%m-%d %H:%M:%S.%f"
        for n in notifs:
            nid = make_uuid()
            ts = n["created_at"].strftime(ts_fmt)
            try:
                cur.execute(
                    """INSERT INTO notification
                        (id, user_id, notification_type, title, message,
                         data, is_read, push_sent, email_sent, sms_sent, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,0,%s)""",
                    (nid, ADMIN_USER_ID, n["type"], n["title"],
                     n["message"], "{}", int(n["is_read"]), ts),
                )
                print(f"  OK - [{n['type']}] {n['title']}")
            except Exception as e:
                print(f"  SKIP [{n['type']}] {n['title']}: {e}")
    conn.commit()


def print_summary(conn: pymysql.Connection) -> None:
    print("\n" + "=" * 60)
    print("SUMMARY — admin@example.com test data")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, email, first_name, last_name, phone, role
            FROM users_user WHERE id=%s""", (ADMIN_USER_ID,))
        row = cur.fetchone()
        if row:
            print(f"  User  : {row[1]} ({row[2]} {row[3]}) | phone={row[4]} | role={row[5]}")

        cur.execute("SELECT license_plate, vehicle_type, brand, model FROM vehicle WHERE user_id=%s", (ADMIN_USER_ID,))
        for r in cur.fetchall():
            print(f"  Vehicle: {r[0]} | {r[1]} | {r[2]} {r[3]}")

        cur.execute("""
            SELECT slot_code, parking_lot_name, check_in_status, payment_status, price, start_time
            FROM booking WHERE user_id=%s ORDER BY start_time DESC""", (ADMIN_USER_ID,))
        bookings = cur.fetchall()
        print(f"  Bookings ({len(bookings)} total):")
        for r in bookings:
            print(f"    [{r[2]:18s}] slot={r[0]:6s} lot={r[1]} pay={r[3]} price={r[4]} start={r[5]}")

        cur.execute("SELECT COUNT(*) FROM payments_payment WHERE user_id=%s", (ADMIN_USER_ID,))
        pcount = cur.fetchone()[0]
        print(f"  Payments: {pcount} records")
    print("=" * 60)


def main() -> None:
    print("ParkSmart — Admin Test Data Seeder")
    print(f"Target: {ADMIN_EMAIL} (id={ADMIN_USER_ID})")
    print(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("-" * 60)

    try:
        conn = get_connection()
    except Exception as e:
        print(f"ERROR: Cannot connect to DB: {e}")
        raise SystemExit(1)

    try:
        update_admin_profile(conn)
        vehicles = seed_vehicles(conn)
        booking_ids = seed_bookings(conn, vehicles)
        seed_payments(conn, booking_ids)
        seed_notifications(conn)
        print_summary(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
