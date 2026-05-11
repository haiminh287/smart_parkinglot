#!/usr/bin/env python3
"""
ParkSmart — Seed ALL 97 slots for Unity Parking Simulator (Vincom Center).

Replaces the entire car_slot set and bookings for Vincom Center lot
with the exact 97 slots that the Unity ParkingLotGenerator creates:
  - V1-01..V1-72 (72 car slots)   — Zone V1
  - V2-01..V2-20 (20 moto slots)  — Zone V2
  - G-01..G-05   (5 garage/car)   — Zone G

Status distribution:
  occupied  = 14 (V1-01..08, V2-01..04, G-01..02)
  reserved  = 11 (V1-09..14, V2-05..08, G-03)
  available = 72 (rest)
  TOTAL     = 97

Creates bookings for chattest@parksmart.com (reserved+occupied slots)
and testdriver@parksmart.com (occupied slots only).

Idempotent — safe to run multiple times.

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_unity_slots.py
"""

import base64
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta

import pymysql

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "parksmartpass"),
    "database": os.environ.get("DB_NAME", "parksmartdb"),
    "charset": "utf8mb4",
}

LOT_ID = "3f54a675e64f4ea9a295ae8b068cc278"
LOT_NAME = "Vincom Center Parking"
FLOOR_ID = "418fa423a86d4f26a29f653bf522c933"
FLOOR_LEVEL = -1

ZONE_V1_ID = "dd657628ec4c477283e0f9b9a85e623d"
ZONE_V2_ID = "ff5416ec518c41439db3fac3e0974b0a"
ZONE_G_ID = None  # resolved at runtime

CHATTEST_EMAIL = "chattest@parksmart.com"
CHATTEST_PASSWORD = "Test@1234"

TESTDRIVER_EMAIL = "testdriver@parksmart.com"
TESTDRIVER_PASSWORD = "Test@1234"

CAR_PLATE = "51G-888.88"
MOTO_PLATE = "59F1-567.89"
TESTDRIVER_CAR_PLATE = "30A-111.11"
TESTDRIVER_MOTO_PLATE = "29B1-234.56"

NOW = datetime.now()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uuid() -> str:
    return uuid.uuid4().hex


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def django_password_hash(password: str) -> str:
    salt = secrets.token_hex(12)
    iterations = 1_000_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"


def get_connection() -> pymysql.Connection:
    return pymysql.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# Slot definitions (97 total)
# ---------------------------------------------------------------------------


def build_slot_specs() -> list[dict]:
    """Build the full list of 97 slot specifications."""
    specs: list[dict] = []

    # V1-01..V1-72 (72 car slots)
    for i in range(1, 73):
        code = f"V1-{i:02d}"
        if i <= 8:
            status = "occupied"
        elif i <= 14:
            status = "reserved"
        else:
            status = "available"
        specs.append({"code": code, "zone_prefix": "V1", "status": status})

    # V2-01..V2-20 (20 moto slots)
    for i in range(1, 21):
        code = f"V2-{i:02d}"
        if i <= 4:
            status = "occupied"
        elif i <= 8:
            status = "reserved"
        else:
            status = "available"
        specs.append({"code": code, "zone_prefix": "V2", "status": status})

    # G-01..G-05 (5 garage/car slots)
    for i in range(1, 6):
        code = f"G-{i:02d}"
        if i <= 2:
            status = "occupied"
        elif i <= 3:
            status = "reserved"
        else:
            status = "available"
        specs.append({"code": code, "zone_prefix": "G", "status": status})

    return specs


# ---------------------------------------------------------------------------
# User + Vehicle helpers
# ---------------------------------------------------------------------------


def ensure_user(
    conn: pymysql.Connection,
    email: str,
    password: str,
    username: str,
    first_name: str,
    last_name: str,
) -> str:
    """Create or find a user. Returns user id."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users_user WHERE email=%s", (email,))
        row = cur.fetchone()
        if row:
            uid = row[0]
            print(f"  EXISTS {email} (id={uid})")
            return uid

        uid = make_uuid()
        pw_hash = django_password_hash(password)
        cur.execute(
            """INSERT INTO users_user
                (id, password, email, username, first_name, last_name,
                 phone, address, role, is_active, is_staff, is_superuser,
                 no_show_count, force_online_payment, date_joined)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                uid,
                pw_hash,
                email,
                username,
                first_name,
                last_name,
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
    print(f"  CREATED {email} (id={uid})")
    return uid


def ensure_vehicle(
    conn: pymysql.Connection,
    user_id: str,
    plate: str,
    vtype: str,
    brand: str,
    model: str,
    color: str,
    is_default: bool,
) -> str:
    """Create or find a vehicle. Returns vehicle id."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM vehicle WHERE license_plate=%s", (plate,))
        row = cur.fetchone()
        if row:
            vid = row[0]
            print(f"  EXISTS vehicle {plate} (id={vid})")
            return vid

        vid = make_uuid()
        cur.execute(
            """INSERT INTO vehicle
                (id, user_id, license_plate, vehicle_type, brand, model,
                 color, is_default, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                vid,
                user_id,
                plate,
                vtype,
                brand,
                model,
                color,
                is_default,
                fmt(NOW),
                fmt(NOW),
            ),
        )
    conn.commit()
    print(f"  CREATED vehicle {plate} ({vtype}) id={vid}")
    return vid


# ---------------------------------------------------------------------------
# Zone G
# ---------------------------------------------------------------------------


def ensure_zone_g(conn: pymysql.Connection) -> str:
    """Create Zone G if it doesn't exist. Returns zone id."""
    global ZONE_G_ID
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM zone WHERE name=%s AND floor_id=%s",
            ("Zone G", FLOOR_ID),
        )
        row = cur.fetchone()
        if row:
            ZONE_G_ID = row[0]
            print(f"  EXISTS Zone G (id={ZONE_G_ID})")
            return ZONE_G_ID

        ZONE_G_ID = make_uuid()
        cur.execute(
            """INSERT INTO zone
                (id, name, vehicle_type, capacity, available_slots,
                 floor_id, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (ZONE_G_ID, "Zone G", "Car", 5, 2, FLOOR_ID, fmt(NOW), fmt(NOW)),
        )
    conn.commit()
    print(f"  CREATED Zone G (id={ZONE_G_ID})")
    return ZONE_G_ID


def get_zone_id(prefix: str) -> str:
    if prefix == "V1":
        return ZONE_V1_ID
    elif prefix == "V2":
        return ZONE_V2_ID
    elif prefix == "G":
        assert ZONE_G_ID is not None, "Zone G must be created first"
        return ZONE_G_ID
    raise ValueError(f"Unknown zone prefix: {prefix}")


def get_zone_name(prefix: str) -> str:
    return {"V1": "Zone V1", "V2": "Zone V2", "G": "Zone G"}[prefix]


def get_vehicle_type(prefix: str) -> str:
    return "Motorbike" if prefix == "V2" else "Car"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_existing(conn: pymysql.Connection) -> None:
    """Delete all existing slots and bookings for Vincom Center."""
    print("\n[1] Cleaning up existing data for Vincom Center...")
    zone_ids = [ZONE_V1_ID, ZONE_V2_ID]
    if ZONE_G_ID:
        zone_ids.append(ZONE_G_ID)

    with conn.cursor() as cur:
        # Delete bookings for this lot
        cur.execute("DELETE FROM booking WHERE parking_lot_id=%s", (LOT_ID,))
        deleted_bookings = cur.rowcount
        print(f"  Deleted {deleted_bookings} bookings")

        # Delete slots for these zones
        if zone_ids:
            placeholders = ",".join(["%s"] * len(zone_ids))
            cur.execute(
                f"DELETE FROM car_slot WHERE zone_id IN ({placeholders})",
                zone_ids,
            )
            deleted_slots = cur.rowcount
            print(f"  Deleted {deleted_slots} slots")

    conn.commit()


# ---------------------------------------------------------------------------
# Create slots
# ---------------------------------------------------------------------------


def create_slots(conn: pymysql.Connection, specs: list[dict]) -> dict[str, str]:
    """Create all 97 slots. Returns dict of slot_code -> slot_id."""
    print(f"\n[3] Creating {len(specs)} slots...")
    slot_map: dict[str, str] = {}

    with conn.cursor() as cur:
        for spec in specs:
            sid = make_uuid()
            zone_id = get_zone_id(spec["zone_prefix"])
            cur.execute(
                """INSERT INTO car_slot
                    (id, code, status, x1, y1, x2, y2,
                     created_at, updated_at, camera_id, zone_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    sid,
                    spec["code"],
                    spec["status"],
                    0,
                    0,
                    0,
                    0,
                    fmt(NOW),
                    fmt(NOW),
                    None,
                    zone_id,
                ),
            )
            slot_map[spec["code"]] = sid

    conn.commit()

    counts = {"available": 0, "occupied": 0, "reserved": 0}
    for spec in specs:
        counts[spec["status"]] += 1
    print(
        f"  Created {len(specs)} slots: "
        f"{counts['occupied']} occupied, {counts['reserved']} reserved, "
        f"{counts['available']} available"
    )
    return slot_map


# ---------------------------------------------------------------------------
# Create bookings
# ---------------------------------------------------------------------------


def create_bookings(
    conn: pymysql.Connection,
    specs: list[dict],
    slot_map: dict[str, str],
    chattest_id: str,
    chattest_vehicles: dict[str, str],
    testdriver_id: str,
    testdriver_vehicles: dict[str, str],
) -> int:
    """Create bookings for occupied and reserved slots."""
    print("\n[4] Creating bookings for occupied/reserved slots...")

    booking_count = 0

    with conn.cursor() as cur:
        for spec in specs:
            if spec["status"] == "available":
                continue

            code = spec["code"]
            prefix = spec["zone_prefix"]
            vtype = get_vehicle_type(prefix)
            zone_id = get_zone_id(prefix)
            zone_name = get_zone_name(prefix)
            slot_id = slot_map[code]
            is_occupied = spec["status"] == "occupied"

            # Decide owner: chattest owns reserved slots + some occupied
            # testdriver owns V1-01..V1-08, V2-01..V2-04, G-01..G-02 (occupied)
            if is_occupied:
                user_id = testdriver_id
                user_email = TESTDRIVER_EMAIL
                if vtype == "Car":
                    plate = TESTDRIVER_CAR_PLATE
                    vehicle_id = testdriver_vehicles[TESTDRIVER_CAR_PLATE]
                else:
                    plate = TESTDRIVER_MOTO_PLATE
                    vehicle_id = testdriver_vehicles[TESTDRIVER_MOTO_PLATE]
                price = 20000.00 if vtype == "Car" else 10000.00
            else:
                # reserved — chattest
                user_id = chattest_id
                user_email = CHATTEST_EMAIL
                if vtype == "Car":
                    plate = CAR_PLATE
                    vehicle_id = chattest_vehicles[CAR_PLATE]
                else:
                    plate = MOTO_PLATE
                    vehicle_id = chattest_vehicles[MOTO_PLATE]
                price = 20000.00 if vtype == "Car" else 10000.00

            if is_occupied:
                start_time = NOW - timedelta(minutes=30)
                check_in_status = "checked_in"
                checked_in_at = fmt(NOW - timedelta(minutes=30))
            else:
                start_time = NOW + timedelta(hours=1)
                check_in_status = "not_checked_in"
                checked_in_at = None

            end_time = start_time + timedelta(hours=4)
            bid = make_uuid()

            qr_data = json.dumps(
                {
                    "booking_id": bid,
                    "slot_code": code,
                    "license_plate": plate,
                    "parking_lot_id": LOT_ID,
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
                    user_email,
                    vehicle_id,
                    plate,
                    vtype,
                    LOT_ID,
                    LOT_NAME,
                    FLOOR_ID,
                    FLOOR_LEVEL,
                    zone_id,
                    zone_name,
                    slot_id,
                    code,
                    "hourly",
                    fmt(start_time),
                    fmt(end_time),
                    "cash",
                    "pending",
                    price,
                    check_in_status,
                    checked_in_at,
                    None,
                    qr_data,
                    False,
                    fmt(NOW),
                    fmt(NOW),
                ),
            )
            booking_count += 1

    conn.commit()
    print(f"  Created {booking_count} bookings")
    return booking_count


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(conn: pymysql.Connection) -> None:
    print("\n" + "=" * 70)
    print("SUMMARY — Vincom Center Unity Slots")
    print("=" * 70)

    with conn.cursor() as cur:
        # Slot counts per zone
        for zone_prefix, zone_id in [
            ("V1", ZONE_V1_ID),
            ("V2", ZONE_V2_ID),
            ("G", ZONE_G_ID),
        ]:
            cur.execute(
                "SELECT status, COUNT(*) FROM car_slot WHERE zone_id=%s GROUP BY status ORDER BY status",
                (zone_id,),
            )
            rows = cur.fetchall()
            total = sum(r[1] for r in rows)
            status_str = ", ".join(f"{r[0]}={r[1]}" for r in rows)
            print(f"  Zone {zone_prefix}: {total} slots ({status_str})")

        # Total
        all_zone_ids = [ZONE_V1_ID, ZONE_V2_ID, ZONE_G_ID]
        placeholders = ",".join(["%s"] * len(all_zone_ids))
        cur.execute(
            f"SELECT COUNT(*) FROM car_slot WHERE zone_id IN ({placeholders})",
            all_zone_ids,
        )
        total_slots = cur.fetchone()[0]
        print(f"  TOTAL: {total_slots} slots")

        # Bookings
        cur.execute(
            "SELECT user_email, check_in_status, COUNT(*) FROM booking "
            "WHERE parking_lot_id=%s GROUP BY user_email, check_in_status "
            "ORDER BY user_email, check_in_status",
            (LOT_ID,),
        )
        rows = cur.fetchall()
        print(f"\n  Bookings:")
        for r in rows:
            print(f"    {r[0]:30s}  {r[1]:18s}  count={r[2]}")

        total_bookings = sum(r[2] for r in rows)
        print(f"  TOTAL: {total_bookings} bookings")

    print("=" * 70)
    print(f"\nCredentials:")
    print(f"  chattest:    {CHATTEST_EMAIL} / {CHATTEST_PASSWORD}")
    print(f"  testdriver:  {TESTDRIVER_EMAIL} / {TESTDRIVER_PASSWORD}")
    print(f"Parking Lot:   {LOT_NAME} (id={LOT_ID})")
    print(f"Slots: V1-01..V1-72, V2-01..V2-20, G-01..G-05 = 97 total")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("ParkSmart — Unity Slots Seeder (97 slots)")
    print(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("-" * 70)

    conn = get_connection()
    try:
        # Step 0: Ensure Zone G exists first (needed for cleanup)
        print("\n[0] Ensuring Zone G exists...")
        ensure_zone_g(conn)

        # Step 1: Cleanup
        cleanup_existing(conn)

        # Step 2: Ensure users + vehicles
        print("\n[2] Ensuring users and vehicles...")
        chattest_id = ensure_user(
            conn,
            CHATTEST_EMAIL,
            CHATTEST_PASSWORD,
            "chattest_unity",
            "Unity",
            "Tester",
        )
        testdriver_id = ensure_user(
            conn,
            TESTDRIVER_EMAIL,
            TESTDRIVER_PASSWORD,
            "testdriver",
            "Test",
            "Driver",
        )

        chattest_vehicles = {
            CAR_PLATE: ensure_vehicle(
                conn,
                chattest_id,
                CAR_PLATE,
                "Car",
                "Toyota",
                "Camry",
                "White",
                True,
            ),
            MOTO_PLATE: ensure_vehicle(
                conn,
                chattest_id,
                MOTO_PLATE,
                "Motorbike",
                "Honda",
                "Wave RSX",
                "Blue",
                False,
            ),
        }
        testdriver_vehicles = {
            TESTDRIVER_CAR_PLATE: ensure_vehicle(
                conn,
                testdriver_id,
                TESTDRIVER_CAR_PLATE,
                "Car",
                "Hyundai",
                "Accent",
                "Black",
                True,
            ),
            TESTDRIVER_MOTO_PLATE: ensure_vehicle(
                conn,
                testdriver_id,
                TESTDRIVER_MOTO_PLATE,
                "Motorbike",
                "Yamaha",
                "Exciter 155",
                "Red",
                False,
            ),
        }

        # Step 3: Create all 97 slots
        specs = build_slot_specs()
        slot_map = create_slots(conn, specs)

        # Step 4: Create bookings
        booking_count = create_bookings(
            conn,
            specs,
            slot_map,
            chattest_id,
            chattest_vehicles,
            testdriver_id,
            testdriver_vehicles,
        )

        # Summary
        print_summary(conn)
        print(f"\nDone! {len(slot_map)} slots + {booking_count} bookings created.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
