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

    def test_dashboard_live_concerns_shows_only_resident_reports_and_settlement(self):
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
        self.assertEqual(payload['summary'], {'total': 3, 'settled': 2, 'active': 1})
        reports_by_subject = {report['subject']: report for report in payload['reports']}
        self.assertNotIn('Private report', reports_by_subject)
        self.assertTrue(reports_by_subject[settled_report.subject]['settled'])
        self.assertEqual(
            reports_by_subject[settled_report.subject]['status_label'],
            'Resolved',
        )
        self.assertFalse(reports_by_subject[active_report.subject]['settled'])
        self.assertTrue(reports_by_subject[closed_report.subject]['settled'])

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
        self.assertEqual(response.json()['summary'], {'total': 1, 'settled': 0, 'active': 1})
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
        self.assertIn('Settled / closed', template)
        self.assertIn('dashboard_live_concerns', template)
        self.assertIn('concerns:list', template)

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
