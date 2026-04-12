#!/usr/bin/env python3
"""
ParkSmart — Seed comprehensive test data for E2E testing.

Creates:
  - Test user (e2e_playwright@parksmart.com) with password TestPass123!
  - Admin user (admin@parksmart.com) with password TestPass123!
  - Vehicles for test user
  - Multiple bookings in different states
  - Payments
  - Notifications

Run from: backend-microservices/ directory
Requires: MySQL running on localhost:3307

Usage:
    python seed_e2e_data.py
"""

import hashlib
import json
import os
import sys
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


def get_connection() -> pymysql.Connection:
    """Get MySQL connection."""
    return pymysql.connect(**DB_CONFIG)


def make_uuid() -> str:
    """Generate a 32-char hex UUID (no hyphens) matching Django's format."""
    return uuid.uuid4().hex


def django_password_hash(password: str) -> str:
    """Create a Django-compatible PBKDF2 password hash.

    Args:
        password: Plain text password.

    Returns:
        Django-format password hash string.
    """
    import base64
    import hashlib
    import secrets

    salt = secrets.token_hex(12)
    iterations = 1000000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"


def seed_users(conn: pymysql.Connection) -> dict[str, str]:
    """Seed test users. Returns dict of email → user_id."""
    users: dict[str, str] = {}
    cursor = conn.cursor()

    test_accounts = [
        {
            "email": "e2e_playwright@parksmart.com",
            "username": "e2e_playwright",
            "first_name": "E2E",
            "last_name": "Tester",
            "role": "user",
            "is_staff": False,
            "is_superuser": False,
        },
        {
            "email": "admin@parksmart.com",
            "username": "admin_parksmart",
            "first_name": "Admin",
            "last_name": "ParkSmart",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
        },
    ]

    password_hash = django_password_hash("TestPass123!")
    admin_password_hash = django_password_hash("admin1234@")

    for acct in test_accounts:
        # Check if exists
        cursor.execute("SELECT id FROM users_user WHERE email = %s", (acct["email"],))
        row = cursor.fetchone()

        current_hash = admin_password_hash if acct["role"] == "admin" else password_hash

        if row:
            user_id = row[0]
            # Update password
            cursor.execute(
                "UPDATE users_user SET password = %s WHERE id = %s",
                (current_hash, user_id),
            )
            print(f"  ✅ Updated password for {acct['email']} (id={user_id})")
        else:
            user_id = make_uuid()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            cursor.execute(
                """INSERT INTO users_user
                (id, email, username, first_name, last_name, password,
                 role, is_staff, is_superuser, is_active, date_joined,
                 no_show_count, force_online_payment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, 0, 0)""",
                (
                    user_id, acct["email"], acct["username"],
                    acct["first_name"], acct["last_name"], current_hash,
                    acct["role"], int(acct["is_staff"]), int(acct["is_superuser"]),
                    now,
                ),
            )
            print(f"  ✅ Created {acct['email']} (id={user_id})")

        users[acct["email"]] = user_id

    conn.commit()
    return users


def seed_vehicles(conn: pymysql.Connection, user_id: str) -> list[str]:
    """Seed vehicles for user. Returns list of vehicle IDs."""
    cursor = conn.cursor()
    vehicles_data = [
        {"plate": "51A-999.88", "type": "car", "brand": "Toyota", "model": "Camry", "color": "White", "default": True},
        {"plate": "59C-123.45", "type": "motorbike", "brand": "Honda", "model": "SH150i", "color": "Black", "default": False},
    ]

    vehicle_ids: list[str] = []

    for v in vehicles_data:
        cursor.execute("SELECT id FROM vehicle WHERE license_plate = %s", (v["plate"],))
        row = cursor.fetchone()
        if row:
            vehicle_ids.append(row[0])
            print(f"  ℹ️ Vehicle {v['plate']} already exists")
            continue

        vid = make_uuid()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        cursor.execute(
            """INSERT INTO vehicle
            (id, user_id, license_plate, vehicle_type, brand, model, color, is_default, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (vid, user_id, v["plate"], v["type"], v["brand"], v["model"],
             v["color"], int(v["default"]), now, now),
        )
        vehicle_ids.append(vid)
        print(f"  ✅ Created vehicle {v['plate']} (id={vid})")

    conn.commit()
    return vehicle_ids


def get_parking_context(conn: pymysql.Connection) -> dict:
    """Get existing parking lot, floor, zone, slot data."""
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT id, name FROM parking_lot LIMIT 1")
    lot = cursor.fetchone()
    if not lot:
        print("  ❌ No parking lots found! Seed parking data first.")
        return {}

    cursor.execute("SELECT id, name, level FROM floor WHERE parking_lot_id = %s LIMIT 1", (lot["id"],))
    floor = cursor.fetchone()

    cursor.execute(
        "SELECT id, name, vehicle_type FROM zone WHERE floor_id = %s LIMIT 1",
        (floor["id"],) if floor else ("",),
    )
    zone = cursor.fetchone()

    cursor.execute(
        "SELECT id, code FROM car_slot WHERE zone_id = %s AND status = 'available' LIMIT 5",
        (zone["id"],) if zone else ("",),
    )
    slots = cursor.fetchall()

    return {
        "lot": lot,
        "floor": floor,
        "zone": zone,
        "slots": slots,
    }


def seed_bookings(
    conn: pymysql.Connection,
    user_id: str,
    user_email: str,
    vehicle_id: str,
    vehicle_plate: str,
    ctx: dict,
) -> list[str]:
    """Seed bookings in various states. Returns list of booking IDs."""
    if not ctx.get("lot") or not ctx.get("slots"):
        print("  ⚠️ No parking context, skipping bookings")
        return []

    cursor = conn.cursor()
    booking_ids: list[str] = []

    now = datetime.now()
    bookings_data = [
        {
            "status": "checked_in",
            "payment_status": "pending",
            "start_time": now - timedelta(hours=2),
            "checked_in_at": now - timedelta(hours=2),
            "price": 15000,
        },
        {
            "status": "completed",
            "payment_status": "completed",
            "start_time": now - timedelta(days=1, hours=3),
            "end_time": now - timedelta(days=1, hours=1),
            "checked_in_at": now - timedelta(days=1, hours=3),
            "checked_out_at": now - timedelta(days=1, hours=1),
            "price": 30000,
        },
        {
            "status": "pending",
            "payment_status": "pending",
            "start_time": now + timedelta(hours=1),
            "price": 10000,
        },
        {
            "status": "completed",
            "payment_status": "completed",
            "start_time": now - timedelta(days=3),
            "end_time": now - timedelta(days=3) + timedelta(hours=4),
            "checked_in_at": now - timedelta(days=3),
            "checked_out_at": now - timedelta(days=3) + timedelta(hours=4),
            "price": 50000,
        },
    ]

    lot = ctx["lot"]
    floor = ctx["floor"]
    zone = ctx["zone"]
    slots = ctx["slots"]

    for i, bdata in enumerate(bookings_data):
        if i >= len(slots):
            break

        slot = slots[i]
        bid = str(uuid.uuid4()).replace("-", "")
        ts_fmt = "%Y-%m-%d %H:%M:%S.%f"
        now_str = now.strftime(ts_fmt)

        cursor.execute(
            """INSERT INTO booking
            (id, user_id, user_email, vehicle_id, vehicle_license_plate, vehicle_type,
             parking_lot_id, parking_lot_name, floor_id, floor_level,
             zone_id, zone_name, slot_id, slot_code,
             package_type, start_time, end_time,
             payment_method, payment_status, price,
             check_in_status, checked_in_at, checked_out_at,
             qr_code_data, created_at, updated_at, late_fee_applied)
            VALUES (%s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, 0)""",
            (
                bid, user_id, user_email, vehicle_id, vehicle_plate, "car",
                lot["id"], lot["name"],
                floor["id"] if floor else None, floor["level"] if floor else None,
                zone["id"], zone["name"], slot["id"], slot["code"],
                "hourly",
                bdata["start_time"].strftime(ts_fmt),
                bdata.get("end_time", bdata["start_time"] + timedelta(hours=2)).strftime(ts_fmt),
                "cash", bdata["payment_status"], bdata["price"],
                bdata["status"],
                bdata.get("checked_in_at", "").strftime(ts_fmt) if bdata.get("checked_in_at") else None,
                bdata.get("checked_out_at", "").strftime(ts_fmt) if bdata.get("checked_out_at") else None,
                bid, now_str, now_str,
            ),
        )
        booking_ids.append(bid)
        print(f"  ✅ Booking {bid[:8]}... ({bdata['status']}, {bdata['price']}đ)")

    conn.commit()
    return booking_ids


def seed_payments(conn: pymysql.Connection, user_id: str, booking_ids: list[str]) -> None:
    """Seed payment records for completed bookings."""
    cursor = conn.cursor()

    for bid in booking_ids[:2]:  # Only seed for first 2 bookings
        pid = str(uuid.uuid4())
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO payments_payment
            (id, booking_id, user_id, payment_method, amount, status, initiated_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id=id""",
            (pid, bid, user_id, "cash", 30000, "completed", now_str, now_str, now_str),
        )
    conn.commit()
    print(f"  ✅ Seeded {min(2, len(booking_ids))} payments")


def seed_notifications(conn: pymysql.Connection, user_id: str) -> None:
    """Seed notifications for test user."""
    cursor = conn.cursor()

    notifs = [
        {
            "type": "booking",
            "title": "Đặt chỗ thành công",
            "message": "Bạn đã đặt chỗ A-01 tại Vincom Center thành công.",
            "is_read": False,
        },
        {
            "type": "payment",
            "title": "Thanh toán hoàn tất",
            "message": "Thanh toán 30.000đ cho booking #12345 đã hoàn tất.",
            "is_read": True,
        },
        {
            "type": "system",
            "title": "Chào mừng đến ParkSmart",
            "message": "Cảm ơn bạn đã đăng ký tài khoản ParkSmart!",
            "is_read": True,
        },
        {
            "type": "alert",
            "title": "Sắp hết thời gian đỗ xe",
            "message": "Booking của bạn sẽ hết hạn trong 30 phút. Gia hạn ngay!",
            "is_read": False,
        },
    ]

    now = datetime.now()
    for i, n in enumerate(notifs):
        nid = make_uuid()
        ts = (now - timedelta(hours=i * 2)).strftime("%Y-%m-%d %H:%M:%S.%f")
        cursor.execute(
            """INSERT INTO notification
            (id, user_id, notification_type, title, message, data, is_read, push_sent, email_sent, sms_sent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0, %s)""",
            (nid, user_id, n["type"], n["title"], n["message"], "{}", int(n["is_read"]), ts),
        )

    conn.commit()
    print(f"  ✅ Seeded {len(notifs)} notifications")


def seed_cameras(conn: pymysql.Connection, ctx: dict) -> None:
    """Seed camera records with proper zone assignments.

    Creates 3 cameras:
      - Camera QR Scanner (HTTP stream, no zone)
      - Camera Biển Số (RTSP stream, no zone)
      - Camera Slot Manager (HTTP stream, assigned to zone)

    Args:
        conn: MySQL connection.
        ctx: Parking context dict with lot/floor/zone info.
    """
    cursor = conn.cursor()

    zone_id = ctx.get("zone", {}).get("id") if ctx.get("zone") else None

    cameras_data = [
        {
            "name": "Camera QR Scanner",
            "ip_address": "192.168.100.130",
            "port": 4747,
            "stream_url": "http://192.168.100.130:4747/video",
            "zone_id": None,  # QR scanner is not tied to a zone
            "is_active": True,
        },
        {
            "name": "Camera Biển Số",
            "ip_address": "192.168.100.23",
            "port": 554,
            "stream_url": "rtsp://user:password@192.168.1.100:554/H.264",
            "zone_id": None,  # License plate camera is not tied to a zone
            "is_active": True,
        },
        {
            "name": "Camera Slot Manager",
            "ip_address": "192.168.100.115",
            "port": 4747,
            "stream_url": "http://192.168.100.115:4747/video",
            "zone_id": zone_id,  # Slot manager monitors a specific zone
            "is_active": True,
        },
    ]

    count = 0
    for cam in cameras_data:
        cursor.execute(
            "SELECT id FROM infrastructure_camera WHERE ip_address = %s AND port = %s",
            (cam["ip_address"], cam["port"]),
        )
        row = cursor.fetchone()

        if row:
            # Update existing camera with zone assignment
            cursor.execute(
                """UPDATE infrastructure_camera
                SET name = %s, stream_url = %s, zone_id = %s, is_active = %s
                WHERE id = %s""",
                (cam["name"], cam["stream_url"], cam["zone_id"], int(cam["is_active"]), row[0]),
            )
            print(f"  ✅ Updated camera {cam['name']} (zone={'assigned' if cam['zone_id'] else 'none'})")
        else:
            cam_id = make_uuid()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            cursor.execute(
                """INSERT INTO infrastructure_camera
                (id, name, ip_address, port, stream_url, zone_id, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    cam_id, cam["name"], cam["ip_address"], cam["port"],
                    cam["stream_url"], cam["zone_id"], int(cam["is_active"]),
                    now, now,
                ),
            )
            print(f"  ✅ Created camera {cam['name']} (zone={'assigned' if cam['zone_id'] else 'none'})")
        count += 1

    conn.commit()
    print(f"  ✅ Seeded {count} cameras total")


def main() -> None:
    """Main seed function."""
    print("=" * 60)
    print("🌱 ParkSmart E2E Test Data Seeder")
    print("=" * 60)

    conn = get_connection()

    try:
        # 1. Users
        print("\n📦 Seeding users...")
        users = seed_users(conn)
        user_id = users["e2e_playwright@parksmart.com"]

        # 2. Vehicles
        print("\n📦 Seeding vehicles...")
        vehicle_ids = seed_vehicles(conn, user_id)

        # 3. Get parking context
        print("\n📦 Checking parking context...")
        ctx = get_parking_context(conn)
        if ctx.get("lot"):
            print(f"  ✅ Lot: {ctx['lot']['name']}")
            print(f"  ✅ Floor: {ctx.get('floor', {}).get('name', 'N/A')}")
            print(f"  ✅ Zone: {ctx.get('zone', {}).get('name', 'N/A')}")
            print(f"  ✅ Available slots: {len(ctx.get('slots', []))}")

        # 4. Bookings
        print("\n📦 Seeding bookings...")
        booking_ids = seed_bookings(
            conn, user_id, "e2e_playwright@parksmart.com",
            vehicle_ids[0] if vehicle_ids else make_uuid(),
            "51A-999.88", ctx,
        )

        # 5. Payments
        print("\n📦 Seeding payments...")
        seed_payments(conn, user_id, booking_ids)

        # 6. Notifications
        print("\n📦 Seeding notifications...")
        seed_notifications(conn, user_id)

        # 7. Cameras
        print("\n📦 Seeding cameras...")
        seed_cameras(conn, ctx)

        print("\n" + "=" * 60)
        print("✅ ALL TEST DATA SEEDED SUCCESSFULLY!")
        print(f"   User: e2e_playwright@parksmart.com / TestPass123!")
        print(f"   Admin: admin@parksmart.com / admin1234@")
        print(f"   Vehicles: {len(vehicle_ids)}")
        print(f"   Bookings: {len(booking_ids)}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
