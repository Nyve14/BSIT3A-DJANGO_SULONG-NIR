from django.test import TestCase
from django.urls import reverse

from .models import Service, ServiceCategory


class ServiceDetailMapTests(TestCase):
    def test_detail_map_shows_streets_with_nir_boundaries(self):
        category = ServiceCategory.objects.create(name='Government')
        service = Service.objects.create(
            name='Test Service',
            category=category,
            latitude='10.900615',
            longitude='122.903860',
        )

        response = self.client.get(
            reverse('public_services:detail', kwargs={'slug': service.slug}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'geojson/nir-provinces.geojson')
        self.assertContains(response, 'geojson/nir-barangays.geojson')
        self.assertContains(response, 'map.setView([lat, lng], 14)')
        self.assertContains(response, 'lat.toFixed(6) +')
        self.assertContains(response, 'serviceMarker.bindPopup(')
        self.assertNotContains(response, 'nir-place-search')
        self.assertNotContains(response, 'Find a place in NIR')
        self.assertNotContains(response, 'function showSelectedPlace()')
        self.assertContains(response, 'L.geoJSON(datasets[0]')
        self.assertContains(response, 'L.circleMarker([lat, lng]')
        self.assertContains(response, 'L.tileLayer(')
        self.assertContains(response, 'tile.openstreetmap.org')
        self.assertContains(response, '&copy; OpenStreetMap contributors')
        self.assertNotContains(response, 'basemaps.cartocdn.com')
