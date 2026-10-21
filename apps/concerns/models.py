import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class GeographicArea(models.Model):
    class Level(models.TextChoices):
        REGION = 'region', 'Region'
        PROVINCE = 'province', 'Province'
        CITY_MUNICIPALITY = 'city_municipality', 'City/Municipality'
        BARANGAY = 'barangay', 'Barangay'

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        null=True,
        blank=True,
    )
    level = models.CharField(max_length=20, choices=Level.choices)
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'geographic_area'
        ordering = ['level', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'name'],
                name='concern_area_parent_name_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_level_display()})'


class ConcernCategory(models.Model):
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'concern_category'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'concern categories'
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'name'],
                name='concern_category_parent_name_uniq',
            ),
        ]

    def __str__(self):
        return self.name


class ConcernReport(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under review'
        REFERRED = 'referred', 'Referred'
        IN_PROGRESS = 'in_progress', 'In progress'
        WAITING_FOR_REPORTER = 'waiting_for_reporter', 'Waiting for reporter'
        RESOLVED = 'resolved', 'Resolved'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        ConcernCategory,
        on_delete=models.PROTECT,
        related_name='reports',
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='concern_reports',
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.SET_NULL,
        related_name='concern_reports',
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_concern_reports',
        null=True,
        blank=True,
    )
    area = models.ForeignKey(
        GeographicArea,
        on_delete=models.PROTECT,
        related_name='reports',
    )
    location_details = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    ai_category = models.CharField(max_length=120, blank=True)
    ai_subcategory = models.CharField(max_length=120, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='ai_duplicate_candidates',
        null=True,
        blank=True,
    )
    ai_duplicate_score = models.FloatField(null=True, blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'concern_report'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(
                fields=['status', 'priority', 'submitted_at'],
                name='concern_status_priority_idx',
            ),
            models.Index(
                fields=['area', 'status', 'submitted_at'],
                name='concern_area_status_idx',
            ),
            models.Index(
                fields=['department', 'status', 'submitted_at'],
                name='concern_dept_status_idx',
            ),
            models.Index(
                fields=['reporter', 'submitted_at'],
                name='concern_reporter_date_idx',
            ),
            models.Index(
                fields=['assigned_to', 'status'],
                name='concern_assignee_status_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(latitude__isnull=True, longitude__isnull=True)
                    | models.Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name='concern_coordinates_together',
            ),
        ]

    def __str__(self):
        return f'{self.subject} ({self.reference})'


class ReportAttachment(models.Model):
    report = models.ForeignKey(
        ConcernReport,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='concern_attachments',
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to='concern_attachments/%Y/%m/')
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_attachment'
        ordering = ['uploaded_at']
        indexes = [
            models.Index(fields=['report', 'uploaded_at'], name='concern_attach_date_idx'),
        ]


class ReportStatusHistory(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        STAFF_ONLY = 'staff_only', 'Staff only'

    report = models.ForeignKey(
        ConcernReport,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='concern_status_changes',
        null=True,
        blank=True,
    )
    old_status = models.CharField(
        max_length=24,
        choices=ConcernReport.Status.choices,
        blank=True,
    )
    new_status = models.CharField(
        max_length=24,
        choices=ConcernReport.Status.choices,
        blank=True,
    )
    comment = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_status_history'
        ordering = ['created_at']
        indexes = [
            models.Index(
                fields=['report', 'created_at'],
                name='concern_history_date_idx',
            ),
        ]


class ReportAssignmentHistory(models.Model):
    report = models.ForeignKey(
        ConcernReport,
        on_delete=models.CASCADE,
        related_name='assignment_history',
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.SET_NULL,
        related_name='concern_assignment_history',
        null=True,
        blank=True,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='concern_assignment_history',
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='concern_assignments_made',
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'report_assignment_history'
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['report'],
                condition=models.Q(ended_at__isnull=True),
                name='concern_one_active_assignment',
            ),
        ]
        indexes = [
            models.Index(
                fields=['report', 'assigned_at'],
                name='concern_assign_date_idx',
            ),
        ]
