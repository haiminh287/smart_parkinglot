import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_alter_incident_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutboxEvent',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('event_id', models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)),
                ('event_type', models.CharField(max_length=64, db_index=True)),
                ('payload', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('published_at', models.DateTimeField(null=True, db_index=True)),
                ('error_count', models.IntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('dead_lettered_at', models.DateTimeField(null=True, db_index=True)),
            ],
            options={
                'indexes': [
                    models.Index(
                        fields=['published_at', 'dead_lettered_at', 'created_at'],
                        name='idx_outbox_pending',
                    ),
                ],
            },
        ),
    ]
