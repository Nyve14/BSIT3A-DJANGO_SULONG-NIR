from decimal import Decimal

from django.db import migrations


def correct_alianza_coordinates(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    service = Service.objects.using(schema_editor.connection.alias).filter(
        slug='alianza-day-care-center',
    ).first()
    if service and (
        service.latitude == Decimal('10.900615')
        and service.longitude == Decimal('122.903860')
    ):
        service.latitude = Decimal('10.473827')
        service.longitude = Decimal('122.929988')
        service.save(update_fields=['latitude', 'longitude'])


def restore_alianza_coordinates(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    service = Service.objects.using(schema_editor.connection.alias).filter(
        slug='alianza-day-care-center',
    ).first()
    if service and (
        service.latitude == Decimal('10.473827')
        and service.longitude == Decimal('122.929988')
    ):
        service.latitude = Decimal('10.900615')
        service.longitude = Decimal('122.903860')
        service.save(update_fields=['latitude', 'longitude'])


class Migration(migrations.Migration):

    dependencies = [
        ('public_services', '0004_correct_bagacay_barangay_hall_coordinates'),
    ]

    operations = [
        migrations.RunPython(
            correct_alianza_coordinates,
            restore_alianza_coordinates,
        ),
    ]
