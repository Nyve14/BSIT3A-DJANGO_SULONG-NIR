from decimal import Decimal

from django.db import migrations


def correct_bagacay_coordinates(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    Service.objects.using(schema_editor.connection.alias).filter(
        slug='bagacay-barangay-hall',
        latitude=Decimal('10.700086'),
        longitude=Decimal('123.046192'),
    ).update(
        latitude=Decimal('9.258872'),
        longitude=Decimal('123.597226'),
    )


def restore_bagacay_coordinates(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    Service.objects.using(schema_editor.connection.alias).filter(
        slug='bagacay-barangay-hall',
        latitude=Decimal('9.258872'),
        longitude=Decimal('123.597226'),
    ).update(
        latitude=Decimal('10.700086'),
        longitude=Decimal('123.046192'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('public_services', '0003_servicecategory_slug'),
    ]

    operations = [
        migrations.RunPython(
            correct_bagacay_coordinates,
            restore_bagacay_coordinates,
        ),
    ]
