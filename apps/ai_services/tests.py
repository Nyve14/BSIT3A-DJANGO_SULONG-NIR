from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.concerns.models import ConcernCategory, ConcernReport


class InsightsSnapshotTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username='insights-admin',
            password='test-password',
        )
        self.client.force_login(user)
        self.snapshot_url = reverse('ai_services:api_insights')

    def create_analyzed_report(self, category_name, ai_category, confidence, subject):
        category, _ = ConcernCategory.objects.get_or_create(name=category_name)
        return ConcernReport.objects.create(
            subject=subject,
            description=f'{subject} details',
            category=category,
            ai_category=ai_category,
            ai_confidence=confidence,
            ai_analyzed_at=timezone.now(),
        )

    def test_live_snapshot_uses_persisted_ai_results(self):
        self.create_analyzed_report(
            'Roads & Infrastructure',
            'roads & infrastructure',
            0.8,
            'Road damage',
        )

        response = self.client.get(self.snapshot_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers['Cache-Control'])
        data = response.json()
        self.assertEqual(data['total_reports'], 1)
        self.assertEqual(data['total_analyzed'], 1)
        self.assertEqual(data['auto_tagged_count'], 1)
        self.assertEqual(data['match_rate'], 100)
        self.assertAlmostEqual(data['avg_confidence'], 0.8)
        self.assertEqual(data['recent_analysis'][0]['confidence'], 80)
        self.assertTrue(data['recent_analysis'][0]['matches_category'])

    def test_next_snapshot_reflects_new_reports(self):
        self.create_analyzed_report('Roads', 'Roads', 0.8, 'Road issue')
        first_response = self.client.get(self.snapshot_url)
        self.assertEqual(first_response.json()['total_reports'], 1)

        self.create_analyzed_report('Utilities', 'Environment', 0.4, 'Water issue')
        second_response = self.client.get(self.snapshot_url)

        self.assertEqual(second_response.json()['total_reports'], 2)
        self.assertEqual(second_response.json()['auto_tagged_count'], 2)
        self.assertEqual(second_response.json()['match_rate'], 50)
        self.assertAlmostEqual(second_response.json()['avg_confidence'], 0.6)

    def test_snapshot_requires_login_and_get(self):
        self.client.logout()
        anonymous_response = self.client.get(self.snapshot_url)
        self.assertEqual(anonymous_response.status_code, 302)

        user = get_user_model().objects.get(username='insights-admin')
        self.client.force_login(user)
        post_response = self.client.post(self.snapshot_url)
        self.assertEqual(post_response.status_code, 405)

    def test_dashboard_renders_live_refresh_controls(self):
        response = self.client.get(reverse('ai_services:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-refresh-interval="15000"')
        self.assertContains(response, 'id="ai-refresh-now"')
        self.assertContains(response, 'id="ai-insight-cards"')
