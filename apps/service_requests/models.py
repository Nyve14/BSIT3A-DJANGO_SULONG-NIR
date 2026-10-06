import uuid

from django.conf import settings
from django.db import models


class ServiceRequest(models.Model):
    class Type(models.TextChoices):
        GENERAL = 'general', 'General'
        TECHNICAL = 'technical', 'Technical support'
        ACCESS = 'access', 'Access'
        MAINTENANCE = 'maintenance', 'Maintenance'
        OTHER = 'other', 'Other'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under review'
        IN_PROGRESS = 'in_progress', 'In progress'
        WAITING = 'waiting', 'Waiting'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    request_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.GENERAL,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_service_requests',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_service_requests',
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.SET_NULL,
        related_name='service_requests',
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tblservicerequest'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', 'priority'], name='sr_status_priority_idx'),
            models.Index(fields=['requester', 'status'], name='sr_requester_status_idx'),
            models.Index(fields=['assigned_to', 'status'], name='sr_assignee_status_idx'),
        ]

    def __str__(self):
        return f'{self.subject} ({self.reference})'


class RequestUpdate(models.Model):
    request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='updates',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='service_request_updates',
        null=True,
        blank=True,
    )
    comment = models.TextField(blank=True)
    previous_status = models.CharField(
        max_length=20,
        choices=ServiceRequest.Status.choices,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=ServiceRequest.Status.choices,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tblrequestupdate'
        ordering = ['created_at']

    def __str__(self):
        return f'Update for {self.request.reference} at {self.created_at:%Y-%m-%d %H:%M}'
