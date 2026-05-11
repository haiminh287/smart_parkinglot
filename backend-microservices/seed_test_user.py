"""Seed test user account để nhận thông báo email.

User account này dùng để bạn login vào web app, đặt chỗ → nhận email notification.

Credentials:
  Email:    minhht2k4@gmail.com
  Username: minhht2k4
  Password: ParkSmart@2026   (đổi sau khi login lần đầu)

Cách chạy:
  cd backend-microservices
  python seed_test_user.py

Yêu cầu: services phải đang chạy (docker compose up -d).
"""
from __future__ import annotations

import sys

import requests

GATEWAY_URL = "http://localhost:8000"

TEST_USER = {
    "email": "minhht2k4@gmail.com",
    "username": "minhht2k4",
    "password": "ParkSmart@2026",
    "phone": "0901234567",
}


def main() -> int:
    print(f"Registering test user via {GATEWAY_URL}/api/auth/register/...")
    try:
        r = requests.post(
            f"{GATEWAY_URL}/api/auth/register/",
            json=TEST_USER,
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"ERROR: Cannot reach gateway — is docker compose up? {e}")
        return 1

    if r.status_code == 201:
        print("✓ User created successfully.")
    elif r.status_code == 400 and "already" in r.text.lower():
        print("✓ User already exists — OK.")
    else:
        print(f"FAILED: status={r.status_code}")
        print(f"Response: {r.text[:500]}")
        return 1

    # Verify login works
    print(f"\nVerifying login...")
    login_r = requests.post(
        f"{GATEWAY_URL}/api/auth/login/",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
        timeout=10,
    )
    if login_r.status_code == 200:
        print(f"✓ Login OK — user: {login_r.json().get('user', {}).get('username')}")
    else:
        print(f"WARN: Login failed ({login_r.status_code}): {login_r.text[:200]}")
        return 1

    print("\n" + "─" * 60)
    print("Tài khoản test sẵn sàng — login vào web app:")
    print(f"  URL:      http://localhost:8080  (hoặc https://parksmart.ghepdoicaulong.shop)")
    print(f"  Email:    {TEST_USER['email']}")
    print(f"  Password: {TEST_USER['password']}")
    print("─" * 60)
    print("\nKhi đặt chỗ → email notification sẽ gửi tới minhht2k4@gmail.com")
    print("(SMTP sender: prolathe633@gmail.com — đã config trong .env)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
