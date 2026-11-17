from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.service_requests.models import RequestUpdate, ServiceRequest


User = get_user_model()


class RequestTrackingTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='requester',
            password='test-password',
        )
        self.other_user = User.objects.create_user(
            username='other',
            password='test-password',
        )
        self.staff = User.objects.create_user(
            username='staff',
            password='test-password',
            is_staff=True,
        )

    def create_request(self, requester=None, **kwargs):
        return ServiceRequest.objects.create(
            requester=requester or self.requester,
            subject='Laptop access',
            description='Please restore access.',
            location='Barangay Poblacion',
            **kwargs,
        )

    def test_requester_can_submit_and_view_own_request(self):
        self.client.force_login(self.requester)
        response = self.client.post(reverse('service_requests:create'), {
            'subject': 'New account',
            'description': 'Please create a system account.',
            'location': 'Barangay Poblacion, Dumaguete City',
            'request_type': ServiceRequest.Type.ACCESS,
            'priority': ServiceRequest.Priority.NORMAL,
            'department': '',
        })

        service_request = ServiceRequest.objects.get(subject='New account')
        self.assertRedirects(
            response,
            reverse('service_requests:detail', args=[service_request.reference]),
        )
        self.assertEqual(service_request.requester, self.requester)
        self.assertEqual(service_request.location, 'Barangay Poblacion, Dumaguete City')
        self.assertTrue(service_request.updates.filter(author=self.requester).exists())

    def test_resident_can_submit_a_barangay_certificate_request(self):
        self.client.force_login(self.requester)
        response = self.client.post(reverse('service_requests:create'), {
            'subject': 'Barangay certificate for school',
            'description': 'I need this for school enrollment.',
            'request_type': ServiceRequest.Type.BARANGAY_CERTIFICATE,
            'priority': ServiceRequest.Priority.NORMAL,
            'department': '',
        })

        service_request = ServiceRequest.objects.get(
            subject='Barangay certificate for school',
        )
        self.assertRedirects(
            response,
            reverse('service_requests:detail', args=[service_request.reference]),
        )
        self.assertEqual(
            service_request.request_type,
            ServiceRequest.Type.BARANGAY_CERTIFICATE,
        )
        self.assertEqual(service_request.requester, self.requester)

    def test_document_request_link_prefills_type_and_title(self):
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse('service_requests:create'),
            {'type': ServiceRequest.Type.CERTIFICATE_OF_INDIGENCY},
        )

        form = response.context['form']
        self.assertEqual(
            form['request_type'].value(),
            ServiceRequest.Type.CERTIFICATE_OF_INDIGENCY,
        )
        self.assertEqual(
            form['subject'].value(),
            'Certificate of indigency request',
        )

    def test_department_field_is_not_in_create_form(self):
        self.client.force_login(self.requester)

        response = self.client.get(reverse('service_requests:create'))

        self.assertNotIn('department', response.context['form'].fields)

    def test_request_detail_does_not_show_department(self):
        service_request = self.create_request(location='Barangay Poblacion')
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse('service_requests:detail', args=[service_request.reference]),
        )

        self.assertNotContains(response, 'Department')
        self.assertContains(response, 'Barangay Poblacion')

    def test_requesters_cannot_view_another_users_request(self):
        service_request = self.create_request(requester=self.other_user)
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse('service_requests:detail', args=[service_request.reference]),
        )

        self.assertEqual(response.status_code, 404)

    def test_staff_status_update_is_recorded(self):
        service_request = self.create_request()
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('service_requests:update', args=[service_request.reference]),
            {
                'status': ServiceRequest.Status.IN_PROGRESS,
                'comment': 'Work has started.',
            },
        )

        service_request.refresh_from_db()
        update = RequestUpdate.objects.get(request=service_request)
        self.assertRedirects(
            response,
            reverse('service_requests:detail', args=[service_request.reference]),
        )
        self.assertEqual(service_request.status, ServiceRequest.Status.IN_PROGRESS)
        self.assertEqual(update.previous_status, ServiceRequest.Status.SUBMITTED)
        self.assertEqual(update.new_status, ServiceRequest.Status.IN_PROGRESS)
        self.assertEqual(update.comment, 'Work has started.')

    def test_requester_can_cancel_own_open_request(self):
        service_request = self.create_request()
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse('service_requests:update', args=[service_request.reference]),
            {'action': 'cancel'},
        )

        service_request.refresh_from_db()
        self.assertRedirects(
            response,
            reverse('service_requests:detail', args=[service_request.reference]),
        )
        self.assertEqual(service_request.status, ServiceRequest.Status.CANCELLED)
        self.assertTrue(
            service_request.updates.filter(
                previous_status=ServiceRequest.Status.SUBMITTED,
                new_status=ServiceRequest.Status.CANCELLED,
            ).exists()
        )
