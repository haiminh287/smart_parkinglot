#!/usr/bin/env python3
"""
ParkSmart — Seed diverse demo data for showcasing the system.

Creates:
  - 3 new parking lots (Aeon Mall Bình Tân, Saigon Centre, Lotte Mart Gò Vấp)
  - 2 floors per lot (B1, B2), each with Car + Motorbike zones
  - Slots with mixed statuses (available, occupied, maintenance)
  - 3 new user accounts
  - Vehicles for each user
  - 10 bookings in diverse states across all lots

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_demo_data.py
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

NOW = datetime.utcnow()

# Existing chattest user
CHATTEST_USER_ID = "fac48257-1270-449d-bf81-a92bf19e9a9c".replace("-", "")
CHATTEST_EMAIL = "chattest@parksmart.com"

# New demo users
DEMO_USERS = [
    {
        "email": "user1@demo.com",
        "username": "nguyen_van_an",
        "first_name": "An",
        "last_name": "Nguyen Van",
        "phone": "0901111111",
    },
    {
        "email": "user2@demo.com",
        "username": "tran_thi_binh",
        "first_name": "Binh",
        "last_name": "Tran Thi",
        "phone": "0902222222",
    },
    {
        "email": "user3@demo.com",
        "username": "le_hoang_cuong",
        "first_name": "Cuong",
        "last_name": "Le Hoang",
        "phone": "0903333333",
    },
]

# New parking lots
PARKING_LOTS = [
    {
        "name": "Aeon Mall Binh Tan",
        "address": "1 Duong so 17A, Binh Tri Dong B, Binh Tan, TP.HCM",
        "latitude": "10.73198000",
        "longitude": "106.61537000",
        "total_slots": 100,
        "price_per_hour": "10000.00",
    },
    {
        "name": "Saigon Centre",
        "address": "65 Le Loi, Ben Nghe, Quan 1, TP.HCM",
        "latitude": "10.77280000",
        "longitude": "106.70040000",
        "total_slots": 80,
        "price_per_hour": "25000.00",
    },
    {
        "name": "Lotte Mart Go Vap",
        "address": "242 Nguyen Van Luong, Go Vap, TP.HCM",
        "latitude": "10.83860000",
        "longitude": "106.65970000",
        "total_slots": 120,
        "price_per_hour": "8000.00",
    },
]


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


# ─── Users ───────────────────────────────────────────


def seed_users(conn: pymysql.Connection) -> dict[str, str]:
    """Seed demo users. Returns {email: user_id}."""
    print("\n[1] Seeding demo users...")
    pw_hash = django_password_hash("Demo@1234")
    users: dict[str, str] = {}

    with conn.cursor() as cur:
        for acct in DEMO_USERS:
            cur.execute("SELECT id FROM users_user WHERE email = %s", (acct["email"],))
            row = cur.fetchone()
            if row:
                uid = row[0]
                print(f"  SKIP {acct['email']} (exists, id={uid})")
            else:
                uid = make_uuid()
                cur.execute(
                    """INSERT INTO users_user
                        (id, password, email, username, first_name, last_name,
                         phone, address, role, is_active, is_staff, is_superuser,
                         no_show_count, force_online_payment, date_joined)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        uid,
                        pw_hash,
                        acct["email"],
                        acct["username"],
                        acct["first_name"],
                        acct["last_name"],
                        acct["phone"],
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
                print(f"  OK - {acct['email']} (id={uid})")
            users[acct["email"]] = uid

    conn.commit()
    return users


# ─── Vehicles ────────────────────────────────────────


def seed_vehicles(conn: pymysql.Connection, users: dict[str, str]) -> dict[str, str]:
    """Seed vehicles. Returns {license_plate: vehicle_id}."""
    print("\n[2] Seeding vehicles...")
    vehicles_spec = [
        {
            "user": "user1@demo.com",
            "plate": "51G-123.45",
            "type": "Car",
            "brand": "Toyota",
            "model": "Vios",
            "color": "White",
            "default": True,
        },
        {
            "user": "user1@demo.com",
            "plate": "59F1-111.11",
            "type": "Motorbike",
            "brand": "Honda",
            "model": "SH 150i",
            "color": "Black",
            "default": False,
        },
        {
            "user": "user2@demo.com",
            "plate": "51H-678.90",
            "type": "Car",
            "brand": "Hyundai",
            "model": "Accent",
            "color": "Silver",
            "default": True,
        },
        {
            "user": "user3@demo.com",
            "plate": "59C1-222.33",
            "type": "Motorbike",
            "brand": "Yamaha",
            "model": "Exciter 155",
            "color": "Red",
            "default": True,
        },
    ]

    result: dict[str, str] = {}
    with conn.cursor() as cur:
        for v in vehicles_spec:
            user_id = users.get(v["user"])
            if not user_id:
                print(f"  WARN - user {v['user']} not found, skipping {v['plate']}")
                continue
            cur.execute(
                "SELECT id FROM vehicle WHERE license_plate = %s", (v["plate"],)
            )
            row = cur.fetchone()
            if row:
                vid = row[0]
                print(f"  SKIP {v['plate']} (exists, id={vid})")
            else:
                vid = make_uuid()
                cur.execute(
                    """INSERT INTO vehicle
                        (id, user_id, license_plate, vehicle_type, brand,
                         model, color, is_default, created_at, updated_at)
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
                print(f"  OK - {v['plate']} ({v['type']}) -> {v['user']}")
            result[v["plate"]] = vid
    conn.commit()
    return result


# ─── Parking Infrastructure ──────────────────────────


def seed_parking_lots(conn: pymysql.Connection) -> list[dict]:
    """Seed 3 parking lots with floors, zones, slots. Returns lot metadata list."""
    print("\n[3] Seeding parking lots + infrastructure...")
    lots_meta: list[dict] = []

    with conn.cursor() as cur:
        for lot_spec in PARKING_LOTS:
            # Check existing
            cur.execute(
                "SELECT id FROM parking_lot WHERE name = %s", (lot_spec["name"],)
            )
            row = cur.fetchone()
            if row:
                lot_id = row[0]
                print(f"  SKIP lot '{lot_spec['name']}' (exists, id={lot_id})")
                # Still gather metadata for bookings
                lot_meta = _gather_lot_meta(conn, lot_id, lot_spec["name"])
                lots_meta.append(lot_meta)
                continue

            lot_id = make_uuid()
            cur.execute(
                """INSERT INTO parking_lot
                    (id, name, address, latitude, longitude,
                     total_slots, available_slots, price_per_hour, is_open,
                     created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    lot_id,
                    lot_spec["name"],
                    lot_spec["address"],
                    lot_spec["latitude"],
                    lot_spec["longitude"],
                    lot_spec["total_slots"],
                    lot_spec["total_slots"],
                    lot_spec["price_per_hour"],
                    True,
                    fmt(NOW),
                    fmt(NOW),
                ),
            )
            print(f"  OK - Lot '{lot_spec['name']}' (id={lot_id})")

            lot_meta = {
                "lot_id": lot_id,
                "lot_name": lot_spec["name"],
                "price": lot_spec["price_per_hour"],
                "floors": [],
            }

            # Create 2 floors: B1 (level=-1), B2 (level=-2)
            for floor_level, floor_name in [(-1, "B1"), (-2, "B2")]:
                floor_id = make_uuid()
                cur.execute(
                    """INSERT INTO floor
                        (id, parking_lot_id, level, name, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (floor_id, lot_id, floor_level, floor_name, fmt(NOW), fmt(NOW)),
                )

                floor_meta = {
                    "floor_id": floor_id,
                    "floor_level": floor_level,
                    "floor_name": floor_name,
                    "zones": [],
                }

                # Car zone
                car_zone_id = make_uuid()
                car_prefix = "A" if floor_name == "B1" else "B"
                car_zone_name = f"Zone {car_prefix} - {floor_name}"
                cur.execute(
                    """INSERT INTO zone
                        (id, floor_id, name, vehicle_type, capacity,
                         available_slots, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        car_zone_id,
                        floor_id,
                        car_zone_name,
                        "Car",
                        15,
                        15,
                        fmt(NOW),
                        fmt(NOW),
                    ),
                )

                car_slots = _create_slots(cur, car_zone_id, car_prefix, 15, "Car")
                floor_meta["zones"].append(
                    {
                        "zone_id": car_zone_id,
                        "zone_name": car_zone_name,
                        "vehicle_type": "Car",
                        "slots": car_slots,
                    }
                )

                # Motorbike zone
                moto_zone_id = make_uuid()
                moto_zone_name = f"Zone M - {floor_name}"
                cur.execute(
                    """INSERT INTO zone
                        (id, floor_id, name, vehicle_type, capacity,
                         available_slots, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        moto_zone_id,
                        floor_id,
                        moto_zone_name,
                        "Motorbike",
                        25,
                        25,
                        fmt(NOW),
                        fmt(NOW),
                    ),
                )

                moto_slots = _create_slots(cur, moto_zone_id, "M", 25, "Motorbike")
                floor_meta["zones"].append(
                    {
                        "zone_id": moto_zone_id,
                        "zone_name": moto_zone_name,
                        "vehicle_type": "Motorbike",
                        "slots": moto_slots,
                    }
                )

                floor_meta["zones"][-1]["slots"] = moto_slots
                lot_meta["floors"].append(floor_meta)

                print(
                    f"    Floor {floor_name}: "
                    f"{car_zone_name} (15 car slots), "
                    f"{moto_zone_name} (25 moto slots)"
                )

            lots_meta.append(lot_meta)

    conn.commit()

    # Update available_slots counts for zones with non-available slots
    _update_available_counts(conn)

    return lots_meta


def _create_slots(
    cur, zone_id: str, prefix: str, count: int, vehicle_type: str
) -> list[dict]:
    """Create slots for a zone. Returns list of {id, code, status}."""
    slots: list[dict] = []
    for i in range(1, count + 1):
        slot_id = make_uuid()
        code = f"{prefix}-{i:02d}"

        # Vary statuses for realism
        if vehicle_type == "Car":
            if i <= 3:
                status = "occupied"
            elif i == 14:
                status = "maintenance"
            else:
                status = "available"
        else:
            if i <= 5:
                status = "occupied"
            elif i == 25:
                status = "maintenance"
            else:
                status = "available"

        cur.execute(
            """INSERT INTO car_slot
                (id, zone_id, code, status, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (slot_id, zone_id, code, status, fmt(NOW), fmt(NOW)),
        )
        slots.append({"id": slot_id, "code": code, "status": status})
    return slots


def _gather_lot_meta(conn: pymysql.Connection, lot_id: str, lot_name: str) -> dict:
    """Gather existing lot metadata for booking creation."""
    meta: dict = {"lot_id": lot_id, "lot_name": lot_name, "floors": []}
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT id, level, name FROM floor WHERE parking_lot_id = %s ORDER BY level",
            (lot_id,),
        )
        floors = cur.fetchall()
        for fl in floors:
            floor_meta = {
                "floor_id": fl["id"],
                "floor_level": fl["level"],
                "floor_name": fl["name"],
                "zones": [],
            }
            cur.execute(
                "SELECT id, name, vehicle_type FROM zone WHERE floor_id = %s",
                (fl["id"],),
            )
            zones = cur.fetchall()
            for z in zones:
                cur.execute(
                    "SELECT id, code, status FROM car_slot "
                    "WHERE zone_id = %s ORDER BY code",
                    (z["id"],),
                )
                slots = [
                    {"id": s["id"], "code": s["code"], "status": s["status"]}
                    for s in cur.fetchall()
                ]
                floor_meta["zones"].append(
                    {
                        "zone_id": z["id"],
                        "zone_name": z["name"],
                        "vehicle_type": z["vehicle_type"],
                        "slots": slots,
                    }
                )
            meta["floors"].append(floor_meta)
    return meta


def _update_available_counts(conn: pymysql.Connection) -> None:
    """Update zone available_slots and lot available_slots counts."""
    with conn.cursor() as cur:
        # Update zone available_slots
        cur.execute(
            """
            UPDATE zone z SET z.available_slots = (
                SELECT COUNT(*) FROM car_slot cs
                WHERE cs.zone_id = z.id AND cs.status = 'available'
            )
        """
        )
        # Update lot available_slots
        cur.execute(
            """
            UPDATE parking_lot pl SET pl.available_slots = (
                SELECT COUNT(*) FROM car_slot cs
                JOIN zone z ON cs.zone_id = z.id
                JOIN floor f ON z.floor_id = f.id
                WHERE f.parking_lot_id = pl.id AND cs.status = 'available'
            )
        """
        )
    conn.commit()


# ─── Bookings ────────────────────────────────────────


def _find_available_slot(lot_meta: dict, vehicle_type: str) -> dict | None:
    """Find first available slot of given vehicle type in lot."""
    for fl in lot_meta.get("floors", []):
        for z in fl.get("zones", []):
            if z["vehicle_type"] != vehicle_type:
                continue
            for s in z.get("slots", []):
                if s["status"] == "available":
                    return {
                        "slot_id": s["id"],
                        "slot_code": s["code"],
                        "zone_id": z["zone_id"],
                        "zone_name": z["zone_name"],
                        "floor_id": fl["floor_id"],
                        "floor_level": fl["floor_level"],
                    }
    return None


def _find_nth_available_slot(
    lot_meta: dict, vehicle_type: str, skip: int = 0
) -> dict | None:
    """Find the Nth available slot (0-indexed skip)."""
    count = 0
    for fl in lot_meta.get("floors", []):
        for z in fl.get("zones", []):
            if z["vehicle_type"] != vehicle_type:
                continue
            for s in z.get("slots", []):
                if s["status"] == "available":
                    if count == skip:
                        return {
                            "slot_id": s["id"],
                            "slot_code": s["code"],
                            "zone_id": z["zone_id"],
                            "zone_name": z["zone_name"],
                            "floor_id": fl["floor_id"],
                            "floor_level": fl["floor_level"],
                        }
                    count += 1
    return None


def seed_bookings(
    conn: pymysql.Connection,
    users: dict[str, str],
    vehicles: dict[str, str],
    lots_meta: list[dict],
) -> list[str]:
    """Seed diverse bookings. Returns booking IDs created."""
    print("\n[4] Seeding bookings...")

    if not lots_meta:
        print("  WARN - No lot metadata, skipping bookings")
        return []

    # Map: lot_name -> lot_meta
    lots_by_name = {m["lot_name"]: m for m in lots_meta}

    aeon = lots_by_name.get("Aeon Mall Binh Tan")
    saigon = lots_by_name.get("Saigon Centre")
    lotte = lots_by_name.get("Lotte Mart Go Vap")

    user1_id = users.get("user1@demo.com", "")
    user2_id = users.get("user2@demo.com", "")
    user3_id = users.get("user3@demo.com", "")
    car1_id = vehicles.get("51G-123.45", "")
    moto1_id = vehicles.get("59F1-111.11", "")
    car2_id = vehicles.get("51H-678.90", "")
    moto3_id = vehicles.get("59C1-222.33", "")

    booking_specs = []

    # 1) user1 checked_in at Aeon (car)
    if aeon:
        slot = _find_nth_available_slot(aeon, "Car", 0)
        if slot:
            booking_specs.append(
                {
                    "user_id": user1_id,
                    "user_email": "user1@demo.com",
                    "vehicle_id": car1_id,
                    "plate": "51G-123.45",
                    "vtype": "Car",
                    "lot": aeon,
                    "slot": slot,
                    "start": NOW - timedelta(hours=1),
                    "end": NOW + timedelta(hours=3),
                    "check_in_status": "checked_in",
                    "checked_in_at": NOW - timedelta(hours=1),
                    "checked_out_at": None,
                    "payment_method": "on_exit",
                    "payment_status": "pending",
                    "price": 10000,
                    "desc": "user1 checked_in @ Aeon (car)",
                }
            )

    # 2) user1 checked_in at Aeon (motorbike)
    if aeon:
        slot = _find_nth_available_slot(aeon, "Motorbike", 0)
        if slot:
            booking_specs.append(
                {
                    "user_id": user1_id,
                    "user_email": "user1@demo.com",
                    "vehicle_id": moto1_id,
                    "plate": "59F1-111.11",
                    "vtype": "Motorbike",
                    "lot": aeon,
                    "slot": slot,
                    "start": NOW - timedelta(hours=2),
                    "end": NOW + timedelta(hours=2),
                    "check_in_status": "checked_in",
                    "checked_in_at": NOW - timedelta(hours=2),
                    "checked_out_at": None,
                    "payment_method": "on_exit",
                    "payment_status": "pending",
                    "price": 5000,
                    "desc": "user1 checked_in @ Aeon (moto)",
                }
            )

    # 3) user2 checked_in at Saigon Centre (car)
    if saigon:
        slot = _find_nth_available_slot(saigon, "Car", 0)
        if slot:
            booking_specs.append(
                {
                    "user_id": user2_id,
                    "user_email": "user2@demo.com",
                    "vehicle_id": car2_id,
                    "plate": "51H-678.90",
                    "vtype": "Car",
                    "lot": saigon,
                    "slot": slot,
                    "start": NOW - timedelta(minutes=30),
                    "end": NOW + timedelta(hours=4),
                    "check_in_status": "checked_in",
                    "checked_in_at": NOW - timedelta(minutes=30),
                    "checked_out_at": None,
                    "payment_method": "online",
                    "payment_status": "completed",
                    "price": 25000,
                    "desc": "user2 checked_in @ Saigon Centre (car)",
                }
            )

    # 4) user1 completed at Saigon Centre 2 days ago
    if saigon:
        slot = _find_nth_available_slot(saigon, "Car", 1)
        if slot:
            booking_specs.append(
                {
                    "user_id": user1_id,
                    "user_email": "user1@demo.com",
                    "vehicle_id": car1_id,
                    "plate": "51G-123.45",
                    "vtype": "Car",
                    "lot": saigon,
                    "slot": slot,
                    "start": NOW - timedelta(days=2, hours=5),
                    "end": NOW - timedelta(days=2, hours=2),
                    "check_in_status": "checked_out",
                    "checked_in_at": NOW - timedelta(days=2, hours=5),
                    "checked_out_at": NOW - timedelta(days=2, hours=2),
                    "payment_method": "online",
                    "payment_status": "completed",
                    "price": 75000,
                    "desc": "user1 completed @ Saigon Centre (2d ago)",
                }
            )

    # 5) user3 completed at Lotte 5 days ago (motorbike)
    if lotte:
        slot = _find_nth_available_slot(lotte, "Motorbike", 0)
        if slot:
            booking_specs.append(
                {
                    "user_id": user3_id,
                    "user_email": "user3@demo.com",
                    "vehicle_id": moto3_id,
                    "plate": "59C1-222.33",
                    "vtype": "Motorbike",
                    "lot": lotte,
                    "slot": slot,
                    "start": NOW - timedelta(days=5, hours=3),
                    "end": NOW - timedelta(days=5, hours=1),
                    "check_in_status": "checked_out",
                    "checked_in_at": NOW - timedelta(days=5, hours=3),
                    "checked_out_at": NOW - timedelta(days=5, hours=1),
                    "payment_method": "on_exit",
                    "payment_status": "completed",
                    "price": 16000,
                    "desc": "user3 completed @ Lotte (5d ago, moto)",
                }
            )

    # 6) user2 completed at Aeon 3 days ago
    if aeon:
        slot = _find_nth_available_slot(aeon, "Car", 1)
        if slot:
            booking_specs.append(
                {
                    "user_id": user2_id,
                    "user_email": "user2@demo.com",
                    "vehicle_id": car2_id,
                    "plate": "51H-678.90",
                    "vtype": "Car",
                    "lot": aeon,
                    "slot": slot,
                    "start": NOW - timedelta(days=3, hours=4),
                    "end": NOW - timedelta(days=3, hours=1),
                    "check_in_status": "checked_out",
                    "checked_in_at": NOW - timedelta(days=3, hours=4),
                    "checked_out_at": NOW - timedelta(days=3, hours=1),
                    "payment_method": "online",
                    "payment_status": "completed",
                    "price": 30000,
                    "desc": "user2 completed @ Aeon (3d ago)",
                }
            )

    # 7) chattest cancelled at Lotte 1 day ago
    if lotte:
        slot = _find_nth_available_slot(lotte, "Car", 0)
        if slot:
            booking_specs.append(
                {
                    "user_id": CHATTEST_USER_ID,
                    "user_email": CHATTEST_EMAIL,
                    "vehicle_id": "",
                    "plate": "51G-888.88",
                    "vtype": "Car",
                    "lot": lotte,
                    "slot": slot,
                    "start": NOW - timedelta(days=1, hours=6),
                    "end": NOW - timedelta(days=1, hours=3),
                    "check_in_status": "cancelled",
                    "checked_in_at": None,
                    "checked_out_at": None,
                    "payment_method": "online",
                    "payment_status": "refunded",
                    "price": 24000,
                    "desc": "chattest cancelled @ Lotte (1d ago)",
                }
            )

    # 8) user1 pending (upcoming) at Lotte tomorrow
    if lotte:
        slot = _find_nth_available_slot(lotte, "Car", 1)
        if slot:
            booking_specs.append(
                {
                    "user_id": user1_id,
                    "user_email": "user1@demo.com",
                    "vehicle_id": car1_id,
                    "plate": "51G-123.45",
                    "vtype": "Car",
                    "lot": lotte,
                    "slot": slot,
                    "start": NOW + timedelta(days=1, hours=9),
                    "end": NOW + timedelta(days=1, hours=12),
                    "check_in_status": "not_checked_in",
                    "checked_in_at": None,
                    "checked_out_at": None,
                    "payment_method": "online",
                    "payment_status": "completed",
                    "price": 24000,
                    "desc": "user1 pending @ Lotte (tomorrow)",
                }
            )

    # 9) user3 pending (upcoming) at Aeon in 2 hours
    if aeon:
        slot = _find_nth_available_slot(aeon, "Motorbike", 1)
        if slot:
            booking_specs.append(
                {
                    "user_id": user3_id,
                    "user_email": "user3@demo.com",
                    "vehicle_id": moto3_id,
                    "plate": "59C1-222.33",
                    "vtype": "Motorbike",
                    "lot": aeon,
                    "slot": slot,
                    "start": NOW + timedelta(hours=2),
                    "end": NOW + timedelta(hours=5),
                    "check_in_status": "not_checked_in",
                    "checked_in_at": None,
                    "checked_out_at": None,
                    "payment_method": "on_exit",
                    "payment_status": "pending",
                    "price": 15000,
                    "desc": "user3 pending @ Aeon (in 2h, moto)",
                }
            )

    # 10) chattest checked_in at Saigon Centre
    if saigon:
        slot = _find_nth_available_slot(saigon, "Car", 2)
        if slot:
            booking_specs.append(
                {
                    "user_id": CHATTEST_USER_ID,
                    "user_email": CHATTEST_EMAIL,
                    "vehicle_id": "",
                    "plate": "51G-888.88",
                    "vtype": "Car",
                    "lot": saigon,
                    "slot": slot,
                    "start": NOW - timedelta(hours=1, minutes=30),
                    "end": NOW + timedelta(hours=2, minutes=30),
                    "check_in_status": "checked_in",
                    "checked_in_at": NOW - timedelta(hours=1, minutes=30),
                    "checked_out_at": None,
                    "payment_method": "on_exit",
                    "payment_status": "pending",
                    "price": 25000,
                    "desc": "chattest checked_in @ Saigon Centre",
                }
            )

    # Resolve chattest vehicle id if needed
    chattest_vehicle_id = ""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM vehicle WHERE license_plate = %s", ("51G-888.88",))
        row = cur.fetchone()
        if row:
            chattest_vehicle_id = row[0]

    booking_ids: list[str] = []
    with conn.cursor() as cur:
        for b in booking_specs:
            # Fix chattest vehicle id
            vid = b["vehicle_id"]
            if b["user_id"] == CHATTEST_USER_ID and not vid:
                vid = chattest_vehicle_id

            slot = b["slot"]
            lot = b["lot"]

            # Check duplicate
            cur.execute(
                "SELECT id FROM booking WHERE user_id = %s AND slot_id = %s "
                "AND start_time = %s",
                (b["user_id"], slot["slot_id"], fmt(b["start"])),
            )
            if cur.fetchone():
                print(f"  SKIP {b['desc']} (already exists)")
                continue

            bid = make_uuid()
            qr_data = json.dumps(
                {
                    "booking_id": bid,
                    "user_id": b["user_id"],
                    "lot": lot["lot_name"],
                    "slot": slot["slot_code"],
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
                    b["user_id"],
                    b["user_email"],
                    vid,
                    b["plate"],
                    b["vtype"],
                    lot["lot_id"],
                    lot["lot_name"],
                    slot["floor_id"],
                    slot["floor_level"],
                    slot["zone_id"],
                    slot["zone_name"],
                    slot["slot_id"],
                    slot["slot_code"],
                    "hourly",
                    fmt(b["start"]),
                    fmt(b["end"]),
                    b["payment_method"],
                    b["payment_status"],
                    b["price"],
                    b["check_in_status"],
                    fmt(b["checked_in_at"]) if b["checked_in_at"] else None,
                    fmt(b["checked_out_at"]) if b["checked_out_at"] else None,
                    qr_data,
                    False,
                    fmt(b["start"]),
                    fmt(NOW),
                ),
            )
            booking_ids.append(bid)
            print(f"  OK - {b['desc']} | slot={slot['slot_code']} | {b['price']}d")

            # Mark slot occupied for checked_in bookings
            if b["check_in_status"] == "checked_in":
                cur.execute(
                    "UPDATE car_slot SET status = 'occupied' WHERE id = %s",
                    (slot["slot_id"],),
                )

    conn.commit()

    # Update available counts after booking slot changes
    _update_available_counts(conn)

    return booking_ids


# ─── Summary ─────────────────────────────────────────


def print_summary(conn: pymysql.Connection, users: dict[str, str]) -> None:
    print("\n" + "=" * 65)
    print("SUMMARY — Demo Data Seeded")
    print("=" * 65)

    with conn.cursor() as cur:
        # Users
        all_emails = list(users.keys())
        if all_emails:
            placeholders = ",".join(["%s"] * len(all_emails))
            cur.execute(
                f"SELECT email, first_name, last_name FROM users_user "
                f"WHERE email IN ({placeholders})",
                all_emails,
            )
            print("  Users:")
            for r in cur.fetchall():
                print(f"    {r[0]} ({r[1]} {r[2]}) | password: Demo@1234")

        # Lots
        for name in [l["name"] for l in PARKING_LOTS]:
            cur.execute(
                "SELECT id, total_slots, available_slots, price_per_hour "
                "FROM parking_lot WHERE name = %s",
                (name,),
            )
            row = cur.fetchone()
            if row:
                print(
                    f"  Lot: {name} | total={row[1]} avail={row[2]} "
                    f"price={row[3]}d/h"
                )

        # Vehicles
        plates = ["51G-123.45", "59F1-111.11", "51H-678.90", "59C1-222.33"]
        placeholders = ",".join(["%s"] * len(plates))
        cur.execute(
            f"SELECT license_plate, vehicle_type, brand, model "
            f"FROM vehicle WHERE license_plate IN ({placeholders})",
            plates,
        )
        print("  Vehicles:")
        for r in cur.fetchall():
            print(f"    {r[0]} | {r[1]} | {r[2]} {r[3]}")

        # Bookings
        all_uids = list(users.values()) + [CHATTEST_USER_ID]
        placeholders = ",".join(["%s"] * len(all_uids))
        cur.execute(
            f"SELECT user_email, slot_code, parking_lot_name, "
            f"check_in_status, payment_status, price "
            f"FROM booking WHERE user_id IN ({placeholders}) "
            f"ORDER BY created_at DESC",
            all_uids,
        )
        rows = cur.fetchall()
        print(f"  Bookings ({len(rows)} total):")
        for r in rows:
            print(
                f"    [{r[3]:18s}] {r[0]:20s} slot={r[1]:6s} "
                f"lot={r[2]} pay={r[4]} price={r[5]}"
            )

    print("=" * 65)


# ─── Main ────────────────────────────────────────────


def main() -> None:
    print("ParkSmart — Demo Data Seeder")
    print(f"DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("-" * 65)

    try:
        conn = get_connection()
    except Exception as e:
        print(f"ERROR: Cannot connect to DB: {e}")
        raise SystemExit(1)

    try:
        users = seed_users(conn)
        vehicles = seed_vehicles(conn, users)
        lots_meta = seed_parking_lots(conn)
        seed_bookings(conn, users, vehicles, lots_meta)
        print_summary(conn, users)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
