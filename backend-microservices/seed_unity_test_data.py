#!/usr/bin/env python3
"""
ParkSmart — Seed test data for the Unity Parking Simulator.

Creates:
  - 1 user account (chattest@parksmart.com / Test@1234)
  - 2 vehicles: Car (51G-888.88) + Motorbike (59F1-567.89)
  - 6 active bookings at Vincom Center (not_checked_in):
      4 Car  → V1-03..V1-06
      2 Moto → V2-03..V2-04
  - Marks V1-01, V1-02 as occupied (existing bookings)

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_unity_test_data.py
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

USER_EMAIL = "chattest@parksmart.com"
USER_PASSWORD = "Test@1234"

VINCOM_LOT = {
    "id": "3f54a675e64f4ea9a295ae8b068cc278",
    "name": "Vincom Center Parking",
    "floor_id": "418fa423a86d4f26a29f653bf522c933",
    "floor_level": -1,
}

ZONES = {
    "V1": {
        "id": "dd657628ec4c477283e0f9b9a85e623d",
        "name": "Zone V1",
        "type": "Car",
    },
    "V2": {
        "id": "ff5416ec518c41439db3fac3e0974b0a",
        "name": "Zone V2",
        "type": "Motorbike",
    },
}

NOW = datetime.now()


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
            print(f"  EXISTS {USER_EMAIL} (id={uid}) — updating password")
            pw_hash = django_password_hash(USER_PASSWORD)
            cur.execute("UPDATE users_user SET password=%s WHERE id=%s", (pw_hash, uid))
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
                uid,
                pw_hash,
                USER_EMAIL,
                "chattest_unity",
                "Unity",
                "Tester",
                "",
                "",
                "user",
                True,
                False,
                False,
                0,
                False,
                fmt(NOW),
            ),
        )
    conn.commit()
    print(f"  OK - {USER_EMAIL} created (id={uid})")
    return uid


def seed_vehicles(conn: pymysql.Connection, user_id: str) -> dict[str, str]:
    print("\n[2] Seeding vehicles...")
    vehicles_data = [
        {
            "plate": "51G-888.88",
            "type": "Car",
            "brand": "Toyota",
            "model": "Camry",
            "color": "White",
            "default": True,
        },
        {
            "plate": "59F1-567.89",
            "type": "Motorbike",
            "brand": "Honda",
            "model": "Wave RSX",
            "color": "Blue",
            "default": False,
        },
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
                    (
                        vid,
                        user_id,
                        v["plate"],
                        v["type"],
                        v["brand"],
                        v["model"],
                        v["color"],
                        v["default"],
                        fmt(NOW),
                        fmt(NOW),
                    ),
                )
                print(f"  OK - {v['plate']} ({v['type']}) id={vid}")
            result[v["plate"]] = vid
    conn.commit()
    return result


def get_slot_id(conn: pymysql.Connection, zone_id: str, slot_code: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM car_slot WHERE zone_id=%s AND code=%s",
            (zone_id, slot_code),
        )
        row = cur.fetchone()
        return row[0] if row else None


def seed_bookings(
    conn: pymysql.Connection, user_id: str, vehicles: dict[str, str]
) -> list[str]:
    print("\n[3] Seeding active bookings at Vincom Center...")

    car_plate = "51G-888.88"
    moto_plate = "59F1-567.89"
    car_id = vehicles[car_plate]
    moto_id = vehicles[moto_plate]

    start_time = NOW
    end_time = NOW + timedelta(hours=4)

    booking_specs = [
        # 4 Car bookings in Zone V1
        {
            "slot_code": "V1-03",
            "zone": "V1",
            "plate": car_plate,
            "vehicle_id": car_id,
            "vtype": "Car",
            "price": 20000,
        },
        {
            "slot_code": "V1-04",
            "zone": "V1",
            "plate": car_plate,
            "vehicle_id": car_id,
            "vtype": "Car",
            "price": 20000,
        },
        {
            "slot_code": "V1-05",
            "zone": "V1",
            "plate": car_plate,
            "vehicle_id": car_id,
            "vtype": "Car",
            "price": 20000,
        },
        {
            "slot_code": "V1-06",
            "zone": "V1",
            "plate": car_plate,
            "vehicle_id": car_id,
            "vtype": "Car",
            "price": 20000,
        },
        # 2 Motorbike bookings in Zone V2
        {
            "slot_code": "V2-03",
            "zone": "V2",
            "plate": moto_plate,
            "vehicle_id": moto_id,
            "vtype": "Motorbike",
            "price": 5000,
        },
        {
            "slot_code": "V2-04",
            "zone": "V2",
            "plate": moto_plate,
            "vehicle_id": moto_id,
            "vtype": "Motorbike",
            "price": 5000,
        },
    ]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for spec in booking_specs:
            zone = ZONES[spec["zone"]]
            slot_id = get_slot_id(conn, zone["id"], spec["slot_code"])
            if not slot_id:
                print(
                    f"  WARN - Slot {spec['slot_code']} not found in zone {spec['zone']}, creating with generated ID"
                )
                slot_id = make_uuid()

            # Check if booking already exists for this user+slot with not_checked_in
            cur.execute(
                "SELECT id FROM booking WHERE user_id=%s AND slot_code=%s AND check_in_status='not_checked_in'",
                (user_id, spec["slot_code"]),
            )
            if cur.fetchone():
                print(f"  SKIP {spec['slot_code']} (active booking exists)")
                continue

            bid = make_uuid()
            qr = json.dumps(
                {
                    "booking_id": bid,
                    "slot_code": spec["slot_code"],
                    "license_plate": spec["plate"],
                    "parking_lot_id": VINCOM_LOT["id"],
                }
            )

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
                    user_id,
                    USER_EMAIL,
                    spec["vehicle_id"],
                    spec["plate"],
                    spec["vtype"],
                    VINCOM_LOT["id"],
                    VINCOM_LOT["name"],
                    VINCOM_LOT["floor_id"],
                    VINCOM_LOT["floor_level"],
                    zone["id"],
                    zone["name"],
                    slot_id,
                    spec["slot_code"],
                    "hourly",
                    fmt(start_time),
                    fmt(end_time),
                    "cash",
                    "pending",
                    spec["price"],
                    "not_checked_in",
                    None,
                    None,
                    qr,
                    False,
                    fmt(NOW),
                    fmt(NOW),
                ),
            )
            booking_ids.append(bid)
            print(
                f"  OK - {spec['slot_code']} ({spec['vtype']}) plate={spec['plate']} price={spec['price']}"
            )

    conn.commit()
    return booking_ids


def mark_occupied_slots(conn: pymysql.Connection) -> None:
    print("\n[4] Marking V1-01, V1-02 as occupied...")
    zone_v1_id = ZONES["V1"]["id"]
    with conn.cursor() as cur:
        for code in ("V1-01", "V1-02"):
            cur.execute(
                "UPDATE car_slot SET status='occupied' WHERE zone_id=%s AND code=%s",
                (zone_v1_id, code),
            )
            if cur.rowcount:
                print(f"  OK - {code} → occupied")
            else:
                print(f"  SKIP - {code} not found or already updated")
    conn.commit()


def print_summary(conn: pymysql.Connection, user_id: str) -> None:
    print("\n" + "=" * 60)
    print(f"SUMMARY — {USER_EMAIL}")
    print("=" * 60)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT email, first_name, last_name, role FROM users_user WHERE id=%s",
            (user_id,),
        )
        r = cur.fetchone()
        if r:
            print(f"  User   : {r[0]} ({r[1]} {r[2]}) | role={r[3]}")

        cur.execute(
            "SELECT license_plate, vehicle_type, brand, model FROM vehicle WHERE user_id=%s",
            (user_id,),
        )
        for r in cur.fetchall():
            print(f"  Vehicle: {r[0]} | {r[1]} | {r[2]} {r[3]}")

        cur.execute(
            "SELECT slot_code, parking_lot_name, check_in_status, payment_status, price "
            "FROM booking WHERE user_id=%s ORDER BY slot_code",
            (user_id,),
        )
        rows = cur.fetchall()
        print(f"  Bookings ({len(rows)} total):")
        for r in rows:
            print(f"    [{r[2]:18s}] slot={r[0]:6s} lot={r[1]} pay={r[3]} price={r[4]}")

        cur.execute(
            "SELECT code, status FROM car_slot WHERE zone_id=%s AND code IN ('V1-01','V1-02') ORDER BY code",
            (ZONES["V1"]["id"],),
        )
        for r in cur.fetchall():
            print(f"  Slot   : {r[0]} → {r[1]}")

    print("=" * 60)
    print(f"\nCredentials:  {USER_EMAIL} / {USER_PASSWORD}")
    print(f"Parking Lot:  {VINCOM_LOT['name']} (id={VINCOM_LOT['id']})")


def main() -> None:
    print("ParkSmart — Unity Simulator Test Data Seeder")
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
        mark_occupied_slots(conn)
        print_summary(conn, user_id)
    finally:
        conn.close()

    print(
        f"\nDone! {len(booking_ids) if 'booking_ids' in dir() else 0} bookings created."
    )


if __name__ == "__main__":
    main()
