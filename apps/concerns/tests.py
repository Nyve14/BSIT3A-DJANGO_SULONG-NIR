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

    def test_emergency_report_is_marked_urgent_for_immediate_action(self):
        public_safety = ConcernCategory.objects.create(name='Public Safety')
        self.client.force_login(self.reporter)

        response = self.client.post(
            f'{reverse("reports:create")}?emergency=1',
            {
                'emergency': '1',
                'subject': 'Traffic accident',
                'description': 'A collision needs immediate assistance.',
                'category': public_safety.pk,
                'province': self.area.pk,
                'city_municipality': '',
                'area': '',
                'location_details': 'Main road near the market',
                'latitude': '10.640700',
                'longitude': '122.955700',
            },
        )

        report = ConcernReport.objects.get(subject='Traffic accident')
        self.assertRedirects(
            response,
            reverse('reports:detail', args=[report.reference]),
        )
        self.assertEqual(report.priority, ConcernReport.Priority.URGENT)
        self.assertTrue(
            report.status_history.filter(
                comment='Emergency report submitted.',
            ).exists()
        )

    def test_emergency_report_sidebar_opens_emergency_form(self):
        self.client.force_login(self.reporter)

        response = self.client.get(reverse('reports:create') + '?emergency=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Emergency report')
        self.assertContains(response, 'Report an emergency')
        self.assertContains(response, 'Submit emergency report')
        self.assertContains(response, 'marked urgent for immediate staff action')
        self.assertNotContains(response, 'Category guide')
        self.assertContains(response, 'Emergency type')
        self.assertContains(response, '>Public Safety</option>')
        self.assertNotContains(response, 'Traffic Accidents')
        self.assertContains(response, 'Emergency title')
        self.assertContains(response, 'What happened and what help is needed?')
        self.assertContains(response, 'Exact emergency location')

    def test_emergency_report_is_red_and_labeled_in_report_list(self):
        emergency_report = self.create_report(
            subject='Emergency accident report',
            priority=ConcernReport.Priority.URGENT,
        )
        ReportStatusHistory.objects.create(
            report=emergency_report,
            actor=self.reporter,
            new_status=ConcernReport.Status.SUBMITTED,
            comment='Emergency report submitted.',
        )
        regular_report = self.create_report(
            subject='Regular urgent report',
            priority=ConcernReport.Priority.URGENT,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse('reports:list'))

        self.assertContains(response, 'Emergency report')
        self.assertContains(
            response,
            'text-danger',
        )
        self.assertContains(response, emergency_report.subject)
        self.assertContains(response, regular_report.subject)
        self.assertEqual(response.status_code, 200)

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

    def test_withdrawn_concern_is_hidden_from_staff_report_list(self):
        withdrawn_report = self.create_report(
            subject='Withdrawn road concern',
            status=ConcernReport.Status.WITHDRAWN,
        )
        visible_report = self.create_report(subject='Active road concern')
        self.client.force_login(self.staff)

        response = self.client.get(reverse('reports:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible_report.subject)
        self.assertNotContains(response, withdrawn_report.subject)

        self.client.force_login(self.reporter)
        resident_response = self.client.get(reverse('reports:list'))

        self.assertContains(resident_response, withdrawn_report.subject)
        self.assertContains(
            resident_response,
            withdrawn_report.get_status_display(),
        )

    def test_withdrawn_concern_is_hidden_from_django_admin(self):
        withdrawn_report = self.create_report(
            subject='Withdrawn admin concern',
            status=ConcernReport.Status.WITHDRAWN,
        )
        visible_report = self.create_report(subject='Visible admin concern')
        admin = User.objects.create_superuser(
            username='reports-admin',
            email='reports-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('admin:concerns_concernreport_changelist'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible_report.subject)
        self.assertNotContains(response, withdrawn_report.subject)

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
        self.assertContains(
            response,
            f'data-updates-url="{reverse("reports:updates", args=[report.reference])}"',
        )
        self.assertContains(response, 'Live · refreshes every 5 seconds')

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

    def test_live_updates_are_visible_only_to_allowed_users(self):
        report = self.create_report()
        ReportStatusHistory.objects.create(
            report=report,
            actor=self.reporter,
            comment='Public progress update.',
            visibility=ReportStatusHistory.Visibility.PUBLIC,
        )
        ReportStatusHistory.objects.create(
            report=report,
            actor=self.staff,
            comment='Internal triage note.',
            visibility=ReportStatusHistory.Visibility.STAFF_ONLY,
        )
        updates_url = reverse('reports:updates', args=[report.reference])

        self.client.force_login(self.reporter)
        resident_response = self.client.get(updates_url)

        self.assertEqual(resident_response.status_code, 200)
        self.assertIn('Public progress update.', resident_response.json()['updates_html'])
        self.assertNotIn('Internal triage note.', resident_response.json()['updates_html'])

        self.client.force_login(self.staff)
        staff_response = self.client.get(updates_url)

        self.assertEqual(staff_response.status_code, 200)
        self.assertIn('Public progress update.', staff_response.json()['updates_html'])
        self.assertIn('Internal triage note.', staff_response.json()['updates_html'])

        other_report = self.create_report(reporter=self.other_user)
        self.client.force_login(self.reporter)
        forbidden_response = self.client.get(
            reverse('reports:updates', args=[other_report.reference]),
        )
        self.assertEqual(forbidden_response.status_code, 404)

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

    def test_resident_can_delete_own_withdrawn_concern(self):
        report = self.create_report(status=ConcernReport.Status.WITHDRAWN)
        self.client.force_login(self.reporter)

        response = self.client.post(
            reverse('reports:delete', args=[report.reference]),
        )

        self.assertRedirects(response, reverse('reports:list'))
        self.assertFalse(ConcernReport.objects.filter(pk=report.pk).exists())

    def test_resident_cannot_delete_active_or_another_residents_concern(self):
        active_report = self.create_report()
        other_withdrawn_report = self.create_report(
            reporter=self.other_user,
            status=ConcernReport.Status.WITHDRAWN,
        )
        self.client.force_login(self.reporter)

        active_response = self.client.post(
            reverse('reports:delete', args=[active_report.reference]),
        )
        other_response = self.client.post(
            reverse('reports:delete', args=[other_withdrawn_report.reference]),
        )

        self.assertEqual(active_response.status_code, 404)
        self.assertEqual(other_response.status_code, 404)
        self.assertTrue(
            ConcernReport.objects.filter(pk=active_report.pk).exists()
        )
        self.assertTrue(
            ConcernReport.objects.filter(pk=other_withdrawn_report.pk).exists()
        )
