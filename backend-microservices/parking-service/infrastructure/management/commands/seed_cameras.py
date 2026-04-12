"""Seed camera data into parking-service database."""

from django.core.management.base import BaseCommand
from infrastructure.models import Camera


class Command(BaseCommand):
    """Create default camera records for the smart parking system."""

    help = "Seed camera data: QR Scanner, Slot Manager, License Plate"

    def handle(self, *_args, **_options):
        cameras = [
            {
                "name": "Camera QR Scanner",
                "ip_address": "192.168.100.130",
                "port": 4747,
                "stream_url": "http://192.168.100.130:4747/video",
                "is_active": True,
            },
            {
                "name": "Camera Slot Manager",
                "ip_address": "192.168.100.115",
                "port": 4747,
                "stream_url": "http://192.168.100.115:4747/video",
                "is_active": True,
            },
            {
                "name": "Camera Biển Số",
                "ip_address": "192.168.100.23",
                "port": 554,
                "stream_url": "rtsp://user:password@192.168.1.100:554/H.264",
                "is_active": True,
            },
        ]

        created_count = 0
        for cam_data in cameras:
            _cam, created = Camera.objects.get_or_create(
                name=cam_data["name"],
                defaults=cam_data,
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Created: {cam_data['name']}")
                )
            else:
                self.stdout.write(f"  ⏭️  Already exists: {cam_data['name']}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! {created_count} camera(s) created."
            )
        )
