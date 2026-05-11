import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("infrastructure", "0002_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessedEvent",
            fields=[
                ("event_id", models.UUIDField(primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=64)),
                (
                    "processed_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "db_table": "processed_events",
            },
        ),
    ]
