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
            subject='Damaged road',
            description='There is a pothole near the market.',
            category=self.category,
            area=self.area,
            **kwargs,
        )

    def test_authenticated_resident_can_submit_concern(self):
        self.client.force_login(self.reporter)
        response = self.client.post(reverse('concerns:create'), {
            'subject': 'Flooded street',
            'description': 'Water collects after rain.',
            'category': self.category.pk,
            'area': self.area.pk,
            'location_details': 'Near the public market',
        })

        report = ConcernReport.objects.get(subject='Flooded street')
        self.assertRedirects(
            response,
            reverse('concerns:detail', args=[report.reference]),
        )
        self.assertEqual(report.reporter, self.reporter)
        self.assertTrue(
            report.status_history.filter(
                actor=self.reporter,
                new_status=ConcernReport.Status.SUBMITTED,
            ).exists()
        )

    def test_report_form_does_not_ask_for_coordinates(self):
        self.client.force_login(self.reporter)
        response = self.client.get(reverse('concerns:create'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Latitude')
        self.assertNotContains(response, 'Longitude')

    def test_reporter_cannot_view_another_residents_concern(self):
        report = self.create_report(reporter=self.other_user)
        self.client.force_login(self.reporter)

        response = self.client.get(
            reverse('concerns:detail', args=[report.reference]),
        )

        self.assertEqual(response.status_code, 404)

    def test_staff_status_and_assignment_changes_are_recorded(self):
        report = self.create_report()
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('concerns:update', args=[report.reference]),
            {
                'status': ConcernReport.Status.IN_PROGRESS,
                'department': '',
                'assigned_to': self.staff.pk,
                'comment': 'A team has been assigned.',
            },
        )

        report.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('concerns:detail', args=[report.reference]),
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
            reverse('concerns:detail', args=[report.reference]),
        )

        self.assertNotContains(response, 'Internal triage note.')

    def test_resident_can_withdraw_own_open_concern(self):
        report = self.create_report()
        self.client.force_login(self.reporter)

        response = self.client.post(
            reverse('concerns:update', args=[report.reference]),
            {'action': 'withdraw'},
        )

        report.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('concerns:detail', args=[report.reference]),
        )
        self.assertEqual(report.status, ConcernReport.Status.WITHDRAWN)
        self.assertTrue(
            report.status_history.filter(
                old_status=ConcernReport.Status.SUBMITTED,
                new_status=ConcernReport.Status.WITHDRAWN,
            ).exists()
        )
