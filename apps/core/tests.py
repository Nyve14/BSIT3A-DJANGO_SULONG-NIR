import json
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.concerns.models import ConcernCategory, ConcernReport, GeographicArea

from .views import dashboard_live_concerns, home, interactive_map


class HomeViewTests(TestCase):
    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username='admin', password='secret1234')

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_requires_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_sidebar_shows_admin_navigation_only_to_superusers(self):
        admin = get_user_model().objects.create_superuser(
            username='sidebar-admin',
            email='sidebar-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        sidebar = response.content.decode().split('<aside', 1)[1].split('</aside>', 1)[0]
        for route_name in (
            'dashboard',
            'interactive_map',
            'users:user_list',
            'info:info_list',
            'ai_services:dashboard',
            'reports:list',
        ):
            self.assertIn(f'href="{reverse(route_name)}"', sidebar)
        for route_name in (
            'service_requests:list',
            'public_services:list',
            'alerts:list',
            'alerts:my_alerts',
        ):
            self.assertNotIn(f'href="{reverse(route_name)}"', sidebar)

    def test_sidebar_shows_concern_links_and_public_services_for_regular_users(self):
        user = get_user_model().objects.create_user(
            username='sidebar-user',
            password='test-password',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        sidebar = response.content.decode().split('<aside', 1)[1].split('</aside>', 1)[0]
        for route_name in ('reports:create', 'reports:list', 'public_services:list'):
            self.assertIn(f'href="{reverse(route_name)}"', sidebar)
        for route_name in (
            'interactive_map',
            'users:user_list',
            'info:info_list',
            'ai_services:dashboard',
            'alerts:list',
            'alerts:my_alerts',
        ):
            self.assertNotIn(f'href="{reverse(route_name)}"', sidebar)

    def test_dashboard_live_concerns_separates_resolved_and_rejected_reports(self):
        resident = get_user_model().objects.create_user(username='dashboard-resident')
        another_resident = get_user_model().objects.create_user(username='another-resident')
        area = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Negros Occidental',
        )
        category = ConcernCategory.objects.create(name='Roads')
        settled_report = ConcernReport.objects.create(
            reporter=resident,
            subject='Settled road issue',
            description='A concern that has been resolved.',
            category=category,
            area=area,
            status=ConcernReport.Status.RESOLVED,
            ai_category='Roads & Infrastructure',
            ai_confidence=0.3,
        )
        active_report = ConcernReport.objects.create(
            reporter=resident,
            subject='Active road issue',
            description='A concern that is being reviewed.',
            category=category,
            area=area,
            status=ConcernReport.Status.IN_PROGRESS,
        )
        closed_report = ConcernReport.objects.create(
            reporter=resident,
            subject='Closed road issue',
            description='A concern that was withdrawn.',
            category=category,
            area=area,
            status=ConcernReport.Status.WITHDRAWN,
        )
        rejected_report = ConcernReport.objects.create(
            reporter=resident,
            subject='Rejected road issue',
            description='A concern that was rejected.',
            category=category,
            area=area,
            status=ConcernReport.Status.REJECTED,
        )
        ConcernReport.objects.create(
            reporter=another_resident,
            subject='Private report',
            description='This report belongs to another resident.',
            category=category,
            area=area,
        )

        self.client.force_login(resident)
        response = self.client.get(reverse('dashboard_live_concerns'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload['summary'],
            {'total': 4, 'resolved': 1, 'closed': 2, 'active': 1},
        )
        reports_by_subject = {report['subject']: report for report in payload['reports']}
        self.assertNotIn('Private report', reports_by_subject)
        self.assertTrue(reports_by_subject[settled_report.subject]['closed'])
        self.assertEqual(
            reports_by_subject[settled_report.subject]['status_label'],
            'Resolved',
        )
        self.assertEqual(
            reports_by_subject[settled_report.subject]['ai_category'],
            'Roads & Infrastructure',
        )
        self.assertEqual(
            reports_by_subject[settled_report.subject]['ai_confidence'],
            0.3,
        )
        self.assertFalse(reports_by_subject[active_report.subject]['closed'])
        self.assertTrue(reports_by_subject[closed_report.subject]['closed'])
        self.assertEqual(
            reports_by_subject[rejected_report.subject]['status_label'],
            'Rejected',
        )

    def test_staff_dashboard_live_concerns_counts_every_report(self):
        resident = get_user_model().objects.create_user(username='staff-view-resident')
        staff = get_user_model().objects.create_user(
            username='dashboard-staff',
            is_staff=True,
        )
        area = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Siquijor',
        )
        category = ConcernCategory.objects.create(name='Drainage')
        ConcernReport.objects.create(
            reporter=resident,
            subject='Siquijor drainage',
            description='A reported drainage concern.',
            category=category,
            area=area,
        )

        self.client.force_login(staff)
        response = self.client.get(reverse('dashboard_live_concerns'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['summary'],
            {'total': 1, 'resolved': 0, 'closed': 0, 'active': 1},
        )
        self.assertEqual(response.json()['reports'][0]['subject'], 'Siquijor drainage')

    def test_dashboard_shows_live_concern_summary_and_all_concerns_link(self):
        user = get_user_model().objects.create_user(username='dashboard-summary-user')
        request = RequestFactory().get(reverse('dashboard'))
        request.user = user

        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            response = home.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(render.call_args.args[1], 'home.html')
        template = (
            Path(__file__).resolve().parents[2]
            / 'templates'
            / 'home.html'
        ).read_text(encoding='utf-8')
        self.assertIn('Concern overview', template)
        self.assertIn('Rejected / withdrawn', template)
        self.assertIn('AI suggestion:', template)
        self.assertIn('dashboard_live_concerns', template)
        self.assertIn('reports:list', template)

    def test_interactive_map_groups_reports_and_limits_resident_data(self):
        resident = get_user_model().objects.create_user(username='resident')
        another_resident = get_user_model().objects.create_user(username='another')
        province = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Negros Occidental',
        )
        city = GeographicArea.objects.create(
            level=GeographicArea.Level.CITY_MUNICIPALITY,
            name='Bacolod City',
            parent=province,
        )
        category = ConcernCategory.objects.create(name='Roads')
        ConcernReport.objects.create(
            reporter=resident,
            subject='Resident concern',
            description='A concern submitted by the signed-in resident.',
            category=category,
            area=city,
        )
        ConcernReport.objects.create(
            reporter=another_resident,
            subject='Other concern',
            description='A concern submitted by another resident.',
            category=category,
            area=city,
        )

        request = RequestFactory().get(reverse('interactive_map'))
        request.user = resident
        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            interactive_map.__wrapped__(request)

        context = render.call_args.args[2]
        occidental = next(
            area for area in context['map_areas']
            if area['name'] == 'Negros Occidental'
        )
        self.assertEqual(occidental['counts'][ConcernReport.Status.SUBMITTED], 1)
        self.assertNotIn('latitude', occidental)
        self.assertNotIn('longitude', occidental)
        self.assertFalse(context['can_view_all_concerns'])

    def test_staff_interactive_map_counts_all_residents_reports(self):
        resident = get_user_model().objects.create_user(username='resident')
        staff = get_user_model().objects.create_user(username='staff', is_staff=True)
        province = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Siquijor',
        )
        category = ConcernCategory.objects.create(name='Drainage')
        ConcernReport.objects.create(
            reporter=resident,
            subject='Drainage concern',
            description='Drainage issue reported in Siquijor.',
            category=category,
            area=province,
        )

        request = RequestFactory().get(reverse('interactive_map'))
        request.user = staff
        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            interactive_map.__wrapped__(request)

        context = render.call_args.args[2]
        siquijor = next(
            area for area in context['map_areas']
            if area['name'] == 'Siquijor'
        )
        self.assertEqual(siquijor['counts'][ConcernReport.Status.SUBMITTED], 1)
        self.assertTrue(context['can_view_all_concerns'])

    def test_interactive_map_includes_barangay_report_dots(self):
        resident = get_user_model().objects.create_user(username='barangay-resident')
        province = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Negros Occidental',
        )
        city = GeographicArea.objects.create(
            level=GeographicArea.Level.CITY_MUNICIPALITY,
            name='Bacolod City (Capital)',
            parent=province,
        )
        barangay = GeographicArea.objects.create(
            level=GeographicArea.Level.BARANGAY,
            name='Alangilan',
            code='PH0604501001',
            parent=city,
        )
        category = ConcernCategory.objects.create(name='Roads')
        ConcernReport.objects.create(
            reporter=resident,
            subject='Active barangay concern',
            description='An open concern in Alangilan.',
            category=category,
            area=barangay,
        )
        ConcernReport.objects.create(
            reporter=resident,
            subject='Settled barangay concern',
            description='A resolved concern in Alangilan.',
            category=category,
            area=barangay,
            status=ConcernReport.Status.RESOLVED,
        )

        request = RequestFactory().get(reverse('interactive_map'))
        request.user = resident
        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            interactive_map.__wrapped__(request)

        context = render.call_args.args[2]
        self.assertEqual(len(context['map_barangays']), 1)
        entry = context['map_barangays'][0]
        self.assertEqual(entry['code'], 'PH0604501001')
        self.assertEqual(entry['name'], 'Alangilan')
        self.assertEqual(entry['municipality'], 'Bacolod City (Capital)')
        self.assertEqual(entry['open'], 1)
        self.assertEqual(entry['settled'], 1)
        self.assertEqual(len(entry['reports']), 2)
        reports_by_subject = {report['subject']: report for report in entry['reports']}
        self.assertFalse(reports_by_subject['Active barangay concern']['settled'])
        self.assertEqual(
            reports_by_subject['Active barangay concern']['status_label'],
            'Submitted',
        )
        self.assertTrue(reports_by_subject['Settled barangay concern']['settled'])
        self.assertRegex(
            reports_by_subject['Active barangay concern']['reference'],
            r'^[0-9a-f-]{36}$',
        )

        template = (
            Path(__file__).resolve().parents[2]
            / 'templates'
            / 'interactive_map.html'
        ).read_text(encoding='utf-8')
        self.assertIn("'nir-barangay-report-dots'", template)
        self.assertIn('#d63939', template)
        self.assertIn('#2f9e44', template)
        self.assertIn('concern-map-barangay-data', template)

    def test_dashboard_does_not_render_map(self):
        user = get_user_model().objects.create_user(username='map-viewer')
        request = RequestFactory().get(reverse('dashboard'))
        request.user = user

        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            response = home.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(render.call_args.args[1], 'home.html')

    def test_interactive_map_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username='map-viewer')
        request = RequestFactory().get(reverse('interactive_map'))
        request.user = user

        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            response = interactive_map.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(render.call_args.args[1], 'interactive_map.html')
        self.assertIn('Negros Occidental', [
            area['name'] for area in render.call_args.args[2]['map_areas']
        ])

    def test_interactive_map_requires_login(self):
        response = self.client.get(reverse('interactive_map'))

        self.assertEqual(response.status_code, 302)

    def test_interactive_map_uses_street_basemap_with_nir_boundaries(self):
        user = get_user_model().objects.create_user(username='nir-map-viewer')
        request = RequestFactory().get(reverse('interactive_map'))
        request.user = user

        with patch('apps.core.views.render', return_value=HttpResponse()) as render:
            response = interactive_map.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        template = (
            Path(__file__).resolve().parents[2]
            / 'templates'
            / 'interactive_map.html'
        ).read_text(encoding='utf-8')
        self.assertIn('nir-only-background', template)
        self.assertIn("'nir-streets':", template)
        self.assertIn("type: 'raster',", template)
        self.assertIn(
            "'https://tile.openstreetmap.de/{z}/{x}/{y}.png'",
            template,
        )
        self.assertIn("id: 'nir-street-basemap'", template)
        self.assertIn('Interactive street map limited to Negros Occidental, Negros Oriental, and Siquijor', template)
        self.assertIn("pitch: 0", template)
        self.assertIn("maxPitch: 0", template)
        self.assertIn('&copy; OpenStreetMap contributors', template)
        self.assertNotIn('cartocdn.com', template)
        self.assertIn("type: 'fill',", template)
        self.assertIn('createNirMask(provinceGeoJSON)', template)
        self.assertIn("'nir-barangay-boundaries'", template)
        self.assertIn("'nir-barangay-names'", template)
        self.assertIn("'nir-barangay-hitarea'", template)
        self.assertIn('nir-map-pulse', template)
        self.assertIn("['feature-state', 'hover']", template)
        self.assertIn('nir-map-total', template)
        self.assertIn('Expected boundaries and counts for only the three NIR provinces.', template)
        self.assertNotIn("'nir-elevation':", template)
        self.assertNotIn("type: 'hillshade'", template)
        self.assertEqual(
            {area['name'] for area in render.call_args.args[2]['map_areas']},
            {'Negros Occidental', 'Negros Oriental', 'Siquijor'},
        )

    def test_bundled_barangay_map_contains_all_nir_barangays(self):
        data_file = (
            Path(__file__).resolve().parents[2]
            / 'static'
            / 'geojson'
            / 'nir-barangays.geojson'
        )
        geojson = json.loads(data_file.read_text(encoding='utf-8'))
        counts = {}
        for feature in geojson['features']:
            properties = feature['properties']
            counts[properties['province']] = counts.get(properties['province'], 0) + 1
            self.assertTrue(properties['name'])
            self.assertTrue(properties['municipality'])
            self.assertTrue(properties['code'])

        self.assertEqual(len(geojson['features']), 1353)
        self.assertEqual(
            counts,
            {
                'Negros Occidental': 662,
                'Negros Oriental': 557,
                'Siquijor': 134,
            },
        )
