from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    ConcernCategory,
    ConcernReport,
    GeographicArea,
    ReportAssignmentHistory,
    ReportStatusHistory,
)

User = get_user_model()


class ConcernWorkflowTests(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            username='resident',
            password='test-password',
        )
        self.other_user = User.objects.create_user(
            username='other-resident',
            password='test-password',
        )
        self.staff = User.objects.create_user(
            username='concern-staff',
            password='test-password',
            is_staff=True,
        )
        self.category = ConcernCategory.objects.create(name='Roads')
        self.area = GeographicArea.objects.create(
            level=GeographicArea.Level.PROVINCE,
            name='Negros Occidental',
        )

    def create_report(self, reporter=None, **kwargs):
        return ConcernReport.objects.create(
            reporter=reporter or self.reporter,
            subject=kwargs.pop('subject', 'Damaged road'),
            description='There is a pothole near the market.',
            category=self.category,
            area=self.area,
            **kwargs,
        )

    def test_authenticated_resident_can_submit_concern(self):
        self.client.force_login(self.reporter)
        response = self.client.post(reverse('reports:create'), {
            'subject': 'Flooded street',
            'description': 'Water collects after rain.',
            'category': self.category.pk,
            'province': self.area.pk,
            'city_municipality': '',
            'area': '',
            'location_details': 'Near the public market',
            'latitude': '10.640700',
            'longitude': '122.955700',
        })

        report = ConcernReport.objects.get(subject='Flooded street')
        self.assertRedirects(
            response,
            reverse('reports:detail', args=[report.reference]),
        )
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(str(report.latitude), '10.640700')
        self.assertEqual(str(report.longitude), '122.955700')
        self.assertTrue(
            report.status_history.filter(
                actor=self.reporter,
                new_status=ConcernReport.Status.SUBMITTED,
            ).exists()
        )

    def test_superuser_does_not_see_new_report_actions(self):
        admin = User.objects.create_superuser(
            username='concern-admin',
            email='concern-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('reports:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All reports')
        self.assertNotContains(response, 'New report')
        self.assertNotContains(response, 'Create report')
        self.assertNotContains(
            response,
            f'href="{reverse("reports:create")}"',
        )

    def test_resident_can_monitor_only_their_own_concerns(self):
        own_report = self.create_report(subject='My road concern')
        other_report = self.create_report(
            reporter=self.other_user,
            subject='Another resident concern',
        )
        self.client.force_login(self.reporter)

        response = self.client.get(reverse('reports:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_report.subject)
        self.assertContains(
            response,
            reverse('reports:detail', args=[own_report.reference]),
        )
        self.assertNotContains(response, other_report.subject)

    def test_report_form_does_not_ask_for_coordinates(self):
        self.client.force_login(self.reporter)
        response = self.client.get(reverse('reports:create'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Latitude')
        self.assertNotContains(response, 'Longitude')
        self.assertContains(response, 'geojson/nir-provinces.geojson')
        self.assertContains(response, 'geojson/nir-barangays.geojson')
        self.assertContains(response, 'nir-provinces.geojson')
        self.assertContains(response, 'maxBoundsViscosity: 1.0')
        self.assertContains(response, 'Choose a province, city, or barangay to zoom to it.')
        self.assertContains(response, 'properties.municipality')
        self.assertContains(response, 'nir-municipality-map-label')
        self.assertContains(response, 'zoom >= 11.5')
        self.assertContains(response, 'connectPlaceSelectors')
        self.assertContains(response, 'barangaysByNameAndMunicipality.get(key)')
        self.assertContains(response, 'pin is near the area center')
        self.assertContains(response, 'No location selected. Click the map to place a pin.')
        self.assertContains(response, "L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'")
        self.assertContains(response, "attribution: '&copy; OpenStreetMap contributors'")
        self.assertContains(response, 'fillOpacity: 0.1')
        self.assertContains(response, 'function getMaskRings()')
        self.assertContains(response, 'outsideRegionMask.setLatLngs(getMaskRings())')
        self.assertContains(response, "fillRule: 'evenodd'")
        self.assertContains(response, 'NIR only · surrounding areas are hidden.')
        self.assertNotContains(response, 'server.arcgisonline.com')
        self.assertNotContains(response, 'basemaps.cartocdn.com')

    def test_reporter_cannot_view_another_residents_concern(self):
        report = self.create_report(reporter=self.other_user)
        self.client.force_login(self.reporter)

        response = self.client.get(
            reverse('reports:detail', args=[report.reference]),
        )

        self.assertEqual(response.status_code, 404)

    def test_staff_concern_management_does_not_show_department(self):
        report = self.create_report()
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse('reports:detail', args=[report.reference]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Department')

    def test_staff_status_and_assignment_changes_are_recorded(self):
        report = self.create_report()
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('reports:update', args=[report.reference]),
            {
                'status': ConcernReport.Status.IN_PROGRESS,
                'assigned_to': self.staff.pk,
                'comment': 'A team has been assigned.',
            },
        )

        report.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('reports:detail', args=[report.reference]),
        )
        self.assertEqual(report.status, ConcernReport.Status.IN_PROGRESS)
        self.assertEqual(report.assigned_to, self.staff)
        self.assertTrue(
            report.status_history.filter(
                old_status=ConcernReport.Status.SUBMITTED,
                new_status=ConcernReport.Status.IN_PROGRESS,
                comment='A team has been assigned.',
            ).exists()
        )
        self.assertTrue(
            ReportAssignmentHistory.objects.filter(
                report=report,
                assignee=self.staff,
                assigned_by=self.staff,
                ended_at__isnull=True,
            ).exists()
        )

    def test_staff_only_note_is_not_shown_to_reporter(self):
        report = self.create_report()
        ReportStatusHistory.objects.create(
            report=report,
            actor=self.staff,
            comment='Internal triage note.',
            visibility=ReportStatusHistory.Visibility.STAFF_ONLY,
        )
        self.client.force_login(self.reporter)

        response = self.client.get(
            reverse('reports:detail', args=[report.reference]),
        )

        self.assertNotContains(response, 'Internal triage note.')

    def test_resident_can_withdraw_own_open_concern(self):
        report = self.create_report()
        self.client.force_login(self.reporter)

        response = self.client.post(
            reverse('reports:update', args=[report.reference]),
            {'action': 'withdraw'},
        )

        report.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('reports:detail', args=[report.reference]),
        )
        self.assertEqual(report.status, ConcernReport.Status.WITHDRAWN)
        self.assertTrue(
            report.status_history.filter(
                old_status=ConcernReport.Status.SUBMITTED,
                new_status=ConcernReport.Status.WITHDRAWN,
            ).exists()
        )
