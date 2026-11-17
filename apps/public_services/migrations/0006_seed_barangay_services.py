from django.db import migrations
from django.utils.text import slugify


def seed_barangay_services(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    ServiceCategory = apps.get_model('public_services', 'ServiceCategory')
    GeographicArea = apps.get_model('concerns', 'GeographicArea')

    categories = {
        name: ServiceCategory.objects.filter(name=name, parent__isnull=False).first()
        for name in ('Barangay Halls', 'Health Centers', 'Daycare Centers')
    }

    barangays = GeographicArea.objects.filter(level='barangay').select_related('parent', 'parent__parent')

    created = 0
    for barangay in barangays:
        municipality = barangay.parent.name if barangay.parent else ''
        province = barangay.parent.parent.name if barangay.parent and barangay.parent.parent else 'Negros Island Region'
        address = f'{barangay.name}, {municipality}, {province}'
        # Use the barangay's unique code (or id) to keep slugs unique across
        # barangays that share the same name (e.g. many "Poblacion" barangays).
        barangay_key = barangay.code or str(barangay.id)

        for label, category in (
            ('Barangay Hall', categories['Barangay Halls']),
            ('Health Center', categories['Health Centers']),
            ('Daycare Center', categories['Daycare Centers']),
        ):
            if category is None:
                continue
            name = f'{barangay.name} {label}'
            slug = slugify(f'{barangay_key} {name}')
            service, was_created = Service.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'barangay': barangay,
                    'category': category,
                    'address': address,
                    'description': f'{label} serving {barangay.name}, {municipality}.',
                    'status': 'active',
                },
            )
            if was_created:
                created += 1


def remove_barangay_services(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    Service.objects.filter(
        name__endswith=' Barangay Hall',
    ).delete()
    Service.objects.filter(
        name__endswith=' Health Center',
    ).delete()
    Service.objects.filter(
        name__endswith=' Daycare Center',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('public_services', '0005_correct_alianza_day_care_center_coordinates'),
        ('concerns', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_barangay_services, remove_barangay_services),
    ]
