from django.db import migrations


def add_emergency_incident_category(apps, schema_editor):
    ConcernCategory = apps.get_model('concerns', 'ConcernCategory')
    ConcernCategory.objects.get_or_create(
        parent=None,
        name='Emergency Incident',
        defaults={
            'description': 'Urgent incidents requiring immediate assistance',
            'is_active': True,
            'sort_order': 25,
        },
    )


def remove_emergency_incident_category(apps, schema_editor):
    ConcernCategory = apps.get_model('concerns', 'ConcernCategory')
    ConcernCategory.objects.filter(
        parent=None,
        name='Emergency Incident',
        reports__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('concerns', '0005_alter_concernreport_area'),
    ]

    operations = [
        migrations.RunPython(
            add_emergency_incident_category,
            remove_emergency_incident_category,
        ),
    ]
