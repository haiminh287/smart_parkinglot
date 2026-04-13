#!/usr/bin/env python3
"""
ParkSmart — Seed comprehensive test data for a regular user (user@example.com).

Creates:
  - 1 regular user account (user@example.com / user123)
  - Profile: Nguyen Van A, phone, address
  - 2 vehicles: Car (VinFast VF8) + Motorbike (Yamaha Exciter)
  - 5 bookings: completed x2, active, upcoming x1, cancelled x1
  - 3 payment records
  - 4 notifications

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_user_test_data.py
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

USER_EMAIL = "user@example.com"
USER_PASSWORD = "user123"

# Lot / floor / zone / slot constants (confirmed from DB)
PARKING_LOTS = {
    "parksmart": {
        "id": "bc1a3e4a0b244510892d2d4b2b64c7b5",
        "name": "ParkSmart Tower",
        "floor_tang2_id": "30098e7d888b4743b0068a331d04b26d",
        "floor_tang2_level": 2,
        "floor_tang3_id": "610fbad6a32445e3ac04917b361f064d",
        "floor_tang3_level": 3,
    },
    "vincom": {
        "id": "3f54a675e64f4ea9a295ae8b068cc278",
        "name": "Vincom Center Parking",
        "floor_id": "418fa423a86d4f26a29f653bf522c933",
        "floor_level": -1,
    },
}

ZONES = {
    # ParkSmart Tower Tang 2
    "C": {"id": "86bf498a7b084f4cbc2d3b0efca0c742", "name": "Zone C", "type": "Motorbike", "lot": "parksmart", "floor_id": "30098e7d888b4743b0068a331d04b26d", "floor_level": 2},
    "D": {"id": "5ef51d4b5cb24dc987eecb1840bc4258", "name": "Zone D", "type": "Motorbike", "lot": "parksmart", "floor_id": "30098e7d888b4743b0068a331d04b26d", "floor_level": 2},
    # ParkSmart Tower Tang 3
    "E": {"id": "9a7588eff5b64b5ab5ba10e55d20223c", "name": "Zone E", "type": "Car",       "lot": "parksmart", "floor_id": "610fbad6a32445e3ac04917b361f064d", "floor_level": 3},
    # Vincom B1
    "V1": {"id": "dd657628ec4c477283e0f9b9a85e623d", "name": "Zone V1", "type": "Car",      "lot": "vincom",    "floor_id": "418fa423a86d4f26a29f653bf522c933", "floor_level": -1},
    "V2": {"id": "ff5416ec518c41439db3fac3e0974b0a", "name": "Zone V2", "type": "Motorbike","lot": "vincom",    "floor_id": "418fa423a86d4f26a29f653bf522c933", "floor_level": -1},
}

NOW = datetime.utcnow()


def get_connection() -> pymysql.Connection:
    return pymysql.connect(**DB_CONFIG)


def make_uuid() -> str:
    return uuid.uuid4().hex


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_micro(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


def django_password_hash(password: str) -> str:
    salt = secrets.token_hex(12)
    iterations = 1_000_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"


def create_user(conn: pymysql.Connection) -> str:
    print("\n[1] Creating user account...")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users_user WHERE email=%s", (USER_EMAIL,))
        row = cur.fetchone()
        if row:
            uid = row[0]
            print(f"  EXISTS user@example.com (id={uid}) — updating profile")
            cur.execute(
                "UPDATE users_user SET first_name=%s, last_name=%s, phone=%s, address=%s WHERE id=%s",
                ("Van A", "Nguyen", "0987654321", "456 Le Loi, Q3, TP.HCM", uid),
            )
            conn.commit()
            return uid

        uid = make_uuid()
        pw_hash = django_password_hash(USER_PASSWORD)
        cur.execute(
            """INSERT INTO users_user
                (id, password, email, username, first_name, last_name,
                 phone, address, role, is_active, is_staff, is_superuser,
                 no_show_count, force_online_payment, date_joined)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                uid, pw_hash, USER_EMAIL, "user_example",
                "Van A", "Nguyen",
                "0987654321", "456 Le Loi, Q3, TP.HCM",
                "user", True, False, False,
                0, False, fmt(NOW),
            ),
        )
    conn.commit()
    print(f"  OK - user@example.com created (id={uid})")
    return uid


def seed_vehicles(conn: pymysql.Connection, user_id: str) -> dict[str, str]:
    print("\n[2] Seeding vehicles...")
    vehicles_data = [
        {"plate": "51A-123.45", "type": "Car",       "brand": "VinFast", "model": "VF8 Plus 2024", "color": "Silver", "default": True},
        {"plate": "59B1-23456", "type": "Motorbike",  "brand": "Yamaha",  "model": "Exciter 155",   "color": "Red",    "default": False},
    ]
    result: dict[str, str] = {}
    with conn.cursor() as cur:
        for v in vehicles_data:
            cur.execute("SELECT id FROM vehicle WHERE license_plate=%s", (v["plate"],))
            row = cur.fetchone()
            if row:
                vid = row[0]
                print(f"  SKIP {v['plate']} (exists, id={vid})")
            else:
                vid = make_uuid()
                cur.execute(
                    """INSERT INTO vehicle
                        (id, user_id, license_plate, vehicle_type, brand, model, color, is_default, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (vid, user_id, v["plate"], v["type"], v["brand"],
                     v["model"], v["color"], v["default"], fmt(NOW), fmt(NOW)),
                )
                print(f"  OK - {v['plate']} ({v['type']}) id={vid}")
            result[v["plate"]] = vid
    conn.commit()
    return result


def get_available_slot(conn: pymysql.Connection, zone_id: str, exclude_ids: list[str]) -> tuple[str, str] | None:
    with conn.cursor() as cur:
        query = "SELECT id, code FROM car_slot WHERE zone_id=%s AND status='available'"
        params: list = [zone_id]
        if exclude_ids:
            query += f" AND id NOT IN ({','.join(['%s']*len(exclude_ids))})"
            params.extend(exclude_ids)
        query += " LIMIT 1"
        cur.execute(query, params)
        row = cur.fetchone()
        return (row[0], row[1]) if row else None


def seed_bookings(conn: pymysql.Connection, user_id: str, vehicles: dict[str, str]) -> list[str]:
    print("\n[3] Seeding bookings...")

    car_plate  = "51A-123.45"
    moto_plate = "59B1-23456"
    car_id  = vehicles.get(car_plate, make_uuid())
    moto_id = vehicles.get(moto_plate, make_uuid())

    # Grab fresh slots
    used: list[str] = []
    s_e   = get_available_slot(conn, ZONES["E"]["id"], used)
    if s_e: used.append(s_e[0])
    s_v1  = get_available_slot(conn, ZONES["V1"]["id"], used)
    if s_v1: used.append(s_v1[0])
    s_c   = get_available_slot(conn, ZONES["C"]["id"], used)
    if s_c: used.append(s_c[0])
    s_d   = get_available_slot(conn, ZONES["D"]["id"], used)
    if s_d: used.append(s_d[0])
    s_v2  = get_available_slot(conn, ZONES["V2"]["id"], used)
    if s_v2: used.append(s_v2[0])

    lot_ps  = PARKING_LOTS["parksmart"]
    lot_vc  = PARKING_LOTS["vincom"]

    bookings = [
        # 1) Completed + cash — 10 days ago
        {
            "lot_id": lot_ps["id"], "lot_name": lot_ps["name"],
            "floor_id": ZONES["E"]["floor_id"], "floor_level": ZONES["E"]["floor_level"],
            "zone": ZONES["E"], "slot": s_e or (make_uuid(), "E-01"),
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW - timedelta(days=10, hours=3),
            "end":   NOW - timedelta(days=10, hours=1),
            "package": "hourly", "pay_method": "cash", "pay_status": "completed",
            "check_status": "checked_out",
            "checked_in":  NOW - timedelta(days=10, hours=3),
            "checked_out": NOW - timedelta(days=10, hours=1),
            "price": 30000, "desc": "Completed/cash/checked_out - ParkSmart Tang 3",
        },
        # 2) Completed + momo — 5 days ago, daily package
        {
            "lot_id": lot_vc["id"], "lot_name": lot_vc["name"],
            "floor_id": lot_vc["floor_id"], "floor_level": lot_vc["floor_level"],
            "zone": ZONES["V1"], "slot": s_v1 or (make_uuid(), "V1-01"),
            "vehicle_id": car_id, "plate": car_plate, "vtype": "Car",
            "start": NOW - timedelta(days=5),
            "end":   NOW - timedelta(days=4),
            "package": "daily", "pay_method": "online", "pay_status": "completed",
            "check_status": "checked_out",
            "checked_in":  NOW - timedelta(days=5),
            "checked_out": NOW - timedelta(days=4),
            "price": 120000, "desc": "Completed/momo/daily - Vincom Tang B1",
        },
        # 3) Active — checked_in (motorbike)
        {
            "lot_id": lot_ps["id"], "lot_name": lot_ps["name"],
            "floor_id": ZONES["C"]["floor_id"], "floor_level": ZONES["C"]["floor_level"],
            "zone": ZONES["C"], "slot": s_c or (make_uuid(), "C-01"),
            "vehicle_id": moto_id, "plate": moto_plate, "vtype": "Motorbike",
            "start": NOW - timedelta(hours=2),
            "end":   NOW + timedelta(hours=1),
            "package": "hourly", "pay_method": "on_exit", "pay_status": "pending",
            "check_status": "checked_in",
            "checked_in":  NOW - timedelta(hours=2),
            "checked_out": None,
            "price": 10000, "desc": "Active/on_exit/checked_in - ParkSmart Tang 2",
        },
        # 4) Upcoming — booked for day after tomorrow
        {
            "lot_id": lot_vc["id"], "lot_name": lot_vc["name"],
            "floor_id": lot_vc["floor_id"], "floor_level": lot_vc["floor_level"],
            "zone": ZONES["V2"], "slot": s_v2 or (make_uuid(), "V2-01"),
            "vehicle_id": moto_id, "plate": moto_plate, "vtype": "Motorbike",
            "start": NOW + timedelta(days=2, hours=8),
            "end":   NOW + timedelta(days=2, hours=10),
            "package": "hourly", "pay_method": "online", "pay_status": "completed",
            "check_status": "not_checked_in",
            "checked_in": None, "checked_out": None,
            "price": 20000, "desc": "Upcoming/online/not_checked_in - Vincom Tang B1",
        },
        # 5) Cancelled motorbike — 2 days ago
        {
            "lot_id": lot_ps["id"], "lot_name": lot_ps["name"],
            "floor_id": ZONES["D"]["floor_id"], "floor_level": ZONES["D"]["floor_level"],
            "zone": ZONES["D"], "slot": s_d or (make_uuid(), "D-01"),
            "vehicle_id": moto_id, "plate": moto_plate, "vtype": "Motorbike",
            "start": NOW - timedelta(days=2, hours=12),
            "end":   NOW - timedelta(days=2, hours=10),
            "package": "hourly", "pay_method": "cash", "pay_status": "refunded",
            "check_status": "cancelled",
            "checked_in": None, "checked_out": None,
            "price": 10000, "desc": "Cancelled/refunded - ParkSmart Tang 2",
        },
    ]

    booking_ids: list[str] = []
    active_slot_id: str | None = None
    with conn.cursor() as cur:
        for b in bookings:
            cur.execute(
                "SELECT id FROM booking WHERE user_id=%s AND slot_id=%s AND start_time=%s",
                (user_id, b["slot"][0], fmt(b["start"])),
            )
            if cur.fetchone():
                print(f"  SKIP {b['desc']} (exists)")
                continue

            bid = make_uuid()
            zone = b["zone"]
            qr = json.dumps({"booking_id": bid, "user_id": user_id, "lot": b["lot_name"], "slot": b["slot"][1]})
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
                    bid, user_id, USER_EMAIL,
                    b["vehicle_id"], b["plate"], b["vtype"],
                    b["lot_id"], b["lot_name"],
                    b["floor_id"], b["floor_level"],
                    zone["id"], zone["name"],
                    b["slot"][0], b["slot"][1],
                    b["package"], fmt(b["start"]), fmt(b["end"]),
                    b["pay_method"], b["pay_status"], b["price"],
                    b["check_status"],
                    fmt(b["checked_in"]) if b["checked_in"] else None,
                    fmt(b["checked_out"]) if b["checked_out"] else None,
                    qr, False,
                    fmt(b["start"]), fmt(NOW),
                ),
            )
            booking_ids.append(bid)
            if b["check_status"] == "checked_in":
                active_slot_id = b["slot"][0]
            print(f"  OK - {b['desc']} | slot={b['slot'][1]}")

    conn.commit()
    if active_slot_id:
        with conn.cursor() as cur:
            cur.execute("UPDATE car_slot SET status='occupied' WHERE id=%s", (active_slot_id,))
        conn.commit()
        print(f"  OK - Marked active slot as occupied")
    return booking_ids


def seed_payments(conn: pymysql.Connection, user_id: str, booking_ids: list[str]) -> None:
    print("\n[4] Seeding payments...")
    payment_data = [
        {"idx": 0, "method": "cash",  "amount": 30000,  "status": "completed", "sfx": "CASH001"},
        {"idx": 1, "method": "momo",  "amount": 120000, "status": "completed", "sfx": "MOMO002"},
        {"idx": 3, "method": "momo",  "amount": 20000,  "status": "completed", "sfx": "MOMO003"},
    ]
    uid8 = user_id[:8].upper()
    with conn.cursor() as cur:
        for p in payment_data:
            idx = p["idx"]
            if idx >= len(booking_ids):
                continue
            bid = booking_ids[idx]
            pid = make_uuid()
            tx_id = f"PS-USER-{uid8}-{p['sfx']}"
            completed_at = fmt_micro(NOW - timedelta(days=10 - idx * 3)) if p["status"] == "completed" else None
            cur.execute(
                """INSERT INTO payments_payment
                    (id, booking_id, user_id, payment_method, amount,
                     transaction_id, status, initiated_at, completed_at,
                     created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE id=id""",
                (
                    pid, bid, user_id, p["method"], p["amount"],
                    tx_id, p["status"],
                    fmt_micro(NOW - timedelta(days=11 - idx * 3)),
                    completed_at,
                    fmt_micro(NOW), fmt_micro(NOW),
                ),
            )
            print(f"  OK - {p['method']} {p['amount']}d tx={tx_id} status={p['status']}")
    conn.commit()


def seed_notifications(conn: pymysql.Connection, user_id: str) -> None:
    print("\n[5] Seeding notifications...")
    notifs = [
        ("booking", "Dat cho thanh cong", "Slot E-01 tai ParkSmart Tower da duoc xac nhan. Giu cho den 10 ngay truoc.", True,  NOW - timedelta(days=10)),
        ("payment", "Thanh toan thanh cong", "Thanh toan 120.000d goi ngay tai Vincom Center qua Momo.", True,  NOW - timedelta(days=5)),
        ("booking", "Booking sap toi", "Nhac nho: ban co booking tai Vincom Center sau 2 ngay luc 08:00.", False, NOW - timedelta(hours=3)),
        ("system",  "Khuyen mai thang 3",  "Giam 20% cho moi booking tu 25-31/03. Ap dung cho goi theo ngay!", False, NOW - timedelta(hours=30)),
    ]
    with conn.cursor() as cur:
        for ntype, title, msg, is_read, created in notifs:
            nid = make_uuid()
            cur.execute(
                """INSERT INTO notifications_notification
                    (id, user_id, notification_type, title, message,
                     data, is_read, push_sent, email_sent, sms_sent, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,0,%s)""",
                (nid, user_id, ntype, title, msg, "{}", int(is_read), fmt_micro(created)),
            )
            print(f"  OK - [{ntype}] {title}")
    conn.commit()


def print_summary(conn: pymysql.Connection, user_id: str) -> None:
    print("\n" + "=" * 60)
    print(f"SUMMARY — {USER_EMAIL}")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute("SELECT email, first_name, last_name, phone, role FROM users_user WHERE id=%s", (user_id,))
        r = cur.fetchone()
        if r:
            print(f"  User   : {r[0]} ({r[1]} {r[2]}) | phone={r[3]} | role={r[4]}")

        cur.execute("SELECT license_plate, vehicle_type, brand, model FROM vehicle WHERE user_id=%s", (user_id,))
        for r in cur.fetchall():
            print(f"  Vehicle: {r[0]} | {r[1]} | {r[2]} {r[3]}")

        cur.execute(
            "SELECT slot_code, parking_lot_name, check_in_status, payment_status, price, DATE(start_time) FROM booking WHERE user_id=%s ORDER BY start_time DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        print(f"  Bookings ({len(rows)} total):")
        for r in rows:
            print(f"    [{r[2]:18s}] slot={r[0]:6s} lot={r[1]} pay={r[3]} price={r[4]} date={r[5]}")

        cur.execute("SELECT COUNT(*) FROM payments_payment WHERE user_id=%s", (user_id,))
        print(f"  Payments: {cur.fetchone()[0]} records")

        cur.execute("SELECT COUNT(*) FROM notifications_notification WHERE user_id=%s", (user_id,))
        print(f"  Notifications: {cur.fetchone()[0]} records")
    print("=" * 60)
    print(f"\nCredentials:  {USER_EMAIL} / {USER_PASSWORD}")


def main() -> None:
    print("ParkSmart — Regular User Test Data Seeder")
    print(f"Target: {USER_EMAIL}")
    print(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("-" * 60)

    try:
        conn = get_connection()
    except Exception as e:
        print(f"ERROR: Cannot connect to DB: {e}")
        raise SystemExit(1)

    try:
        user_id = create_user(conn)
        vehicles = seed_vehicles(conn, user_id)
        booking_ids = seed_bookings(conn, user_id, vehicles)
        seed_payments(conn, user_id, booking_ids)
        seed_notifications(conn, user_id)
        print_summary(conn, user_id)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
