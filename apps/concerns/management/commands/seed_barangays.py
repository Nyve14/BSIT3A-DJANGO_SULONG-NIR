import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.concerns.models import GeographicArea


class Command(BaseCommand):
    help = 'Seed city/municipality and barangay GeographicArea rows from the bundled NIR GeoJSON.'

    def handle(self, *args, **options):
        data_file = (
            Path(settings.BASE_DIR) / 'static' / 'geojson' / 'nir-barangays.geojson'
        )
        geojson = json.loads(data_file.read_text(encoding='utf-8'))

        provinces = {
            area.name.casefold(): area
            for area in GeographicArea.objects.filter(
                level=GeographicArea.Level.PROVINCE,
            )
        }
        municipalities = {}
        created_cities = 0
        created_barangays = 0

        for feature in geojson['features']:
            properties = feature['properties']
            province = provinces.get(properties['province'].casefold())
            if province is None:
                self.stderr.write(f"Unknown province: {properties['province']}")
                continue

            municipality_key = (province.id, properties['municipality'])
            municipality = municipalities.get(municipality_key)
            if municipality is None:
                municipality, created = GeographicArea.objects.get_or_create(
                    parent=province,
                    level=GeographicArea.Level.CITY_MUNICIPALITY,
                    name=properties['municipality'],
                )
                if created:
                    created_cities += 1
                municipalities[municipality_key] = municipality

            _, created = GeographicArea.objects.get_or_create(
                parent=municipality,
                level=GeographicArea.Level.BARANGAY,
                name=properties['name'],
                defaults={'code': properties['code']},
            )
            if created:
                created_barangays += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created_cities} cit{"y" if created_cities == 1 else "ies"}/municipalities '
            f'and {created_barangays} barangays.'
        ))
