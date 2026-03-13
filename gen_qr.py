"""Generate QR code for hardware testing."""

import json
import os

import qrcode


def main() -> None:
    """Generate QR code PNG with booking data."""
    data = json.dumps({
        "booking_id": "22d97af3-40c0-4271-b89a-85c5145a364e",
        "user_id": "ecab8dcb-d320-4d63-8283-98094e3ac486",
    })
    img = qrcode.make(data)
    path = os.path.join(
        r"C:\Users\MINH\Documents\Zalo_Received_Files\Project_Main",
        "qr_checkin.png",
    )
    img.save(path)
    print(f"✅ QR code saved to: {path}")
    print(f"   Data: {data}")


if __name__ == "__main__":
    main()
