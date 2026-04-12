from django.core.management.base import BaseCommand
from bookings.models import PackagePricing


PRICING_DATA = [
    {"package_type": "hourly", "vehicle_type": "Car", "price": "15000.00"},
    {"package_type": "hourly", "vehicle_type": "Motorbike", "price": "5000.00"},
    {"package_type": "daily", "vehicle_type": "Car", "price": "80000.00", "duration_days": 1},
    {"package_type": "daily", "vehicle_type": "Motorbike", "price": "20000.00", "duration_days": 1},
    {"package_type": "weekly", "vehicle_type": "Car", "price": "400000.00", "duration_days": 7},
    {"package_type": "weekly", "vehicle_type": "Motorbike", "price": "100000.00", "duration_days": 7},
    {"package_type": "monthly", "vehicle_type": "Car", "price": "1200000.00", "duration_days": 30},
    {"package_type": "monthly", "vehicle_type": "Motorbike", "price": "300000.00", "duration_days": 30},
]


class Command(BaseCommand):
    help = "Seed default PackagePricing data"

    def handle(self, *args, **options):
        created = 0
        for item in PRICING_DATA:
            obj, is_new = PackagePricing.objects.update_or_create(
                package_type=item["package_type"],
                vehicle_type=item["vehicle_type"],
                defaults={"price": item["price"], "duration_days": item.get("duration_days")},
            )
            if is_new:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(PRICING_DATA)} pricing entries ({created} new)."
            )
        )
