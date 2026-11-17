import json
from pathlib import Path

from django.db import migrations


def _iter_coords(geometry):
    geom_type = geometry['type']
    coords = geometry['coordinates']
    if geom_type == 'Polygon':
        for ring in coords:
            for point in ring:
                yield point
    elif geom_type == 'MultiPolygon':
        for polygon in coords:
            for ring in polygon:
                for point in ring:
                    yield point


def _centroid(geometry):
    min_lng = float('inf')
    max_lng = float('-inf')
    min_lat = float('inf')
    max_lat = float('-inf')
    count = 0
    for lng, lat in _iter_coords(geometry):
        if lng < min_lng:
            min_lng = lng
        if lng > max_lng:
            max_lng = lng
        if lat < min_lat:
            min_lat = lat
        if lat > max_lat:
            max_lat = lat
        count += 1
    if count == 0:
        return None
    return (min_lat + max_lat) / 2, (min_lng + max_lng) / 2


def assign_barangay_centroids(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    GeographicArea = apps.get_model('concerns', 'GeographicArea')

    geojson_path = Path(__file__).resolve().parents[3] / 'static' / 'geojson' / 'nir-barangays.geojson'
    with open(geojson_path, encoding='utf-8') as fh:
        features = json.load(fh)['features']

    centroids = {}
    for feature in features:
        props = feature.get('properties', {})
        key = (props.get('name'), props.get('municipality'), props.get('province'))
        center = _centroid(feature.get('geometry') or {})
        if center:
            centroids[key] = center

    barangays = GeographicArea.objects.filter(level='barangay').select_related('parent', 'parent__parent')
    updated = 0
    for barangay in barangays:
        municipality = barangay.parent.name if barangay.parent else ''
        province = barangay.parent.parent.name if barangay.parent and barangay.parent.parent else ''
        center = centroids.get((barangay.name, municipality, province))
        if not center:
            continue
        lat, lng = center
        updated += Service.objects.filter(
            barangay=barangay,
            latitude__isnull=True,
            longitude__isnull=True,
        ).update(latitude=lat, longitude=lng)


def clear_barangay_centroids(apps, schema_editor):
    Service = apps.get_model('public_services', 'Service')
    # Only clear coordinates that were derived from barangay centroids:
    # services whose name ends with the seeded facility labels.
    for suffix in (' Barangay Hall', ' Health Center', ' Daycare Center'):
        Service.objects.filter(name__endswith=suffix).update(latitude=None, longitude=None)


class Migration(migrations.Migration):

    dependencies = [
        ('public_services', '0006_seed_barangay_services'),
        ('concerns', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(assign_barangay_centroids, clear_barangay_centroids),
    ]
