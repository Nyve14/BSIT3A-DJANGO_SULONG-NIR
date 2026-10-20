import uuid

from django.conf import settings
from django.db import models


class AlertChannel(models.TextChoices):
    IN_APP = 'in_app', 'In-App Notification'
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    PUSH = 'push', 'Push Notification'
    WEBHOOK = 'webhook', 'Webhook'


class AlertSeverity(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    CRITICAL = 'critical', 'Critical'
    EMERGENCY = 'emergency', 'Emergency'


class AlertScope(models.TextChoices):
    SYSTEM_WIDE = 'system_wide', 'System-wide (all users)'
    PROVINCE = 'province', 'Province-level'
    CITY_MUNICIPALITY = 'city_municipality', 'City/Municipality-level'
    BARANGAY = 'barangay', 'Barangay-level'
    CUSTOM = 'custom', 'Custom user group'


class EmergencyAlert(models.Model):
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(
        max_length=15,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
    )
    scope = models.CharField(
        max_length=20,
        choices=AlertScope.choices,
        default=AlertScope.SYSTEM_WIDE,
    )
    target_areas = models.ManyToManyField(
        'concerns.GeographicArea',
        blank=True,
        related_name='emergency_alerts',
        help_text='Specific areas for province/city/barangay scope',
    )
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='targeted_alerts',
        help_text='Specific users for custom scope',
    )
    channels = models.JSONField(
        default=list,
        help_text='List of channels: in_app, email, sms, push, webhook',
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_emergency_alerts',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'emergency_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'severity', 'created_at'], name='alert_active_sev_idx'),
            models.Index(fields=['sent_at', 'expires_at'], name='alert_sent_exp_idx'),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_severity_display()})'


class AlertDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        READ = 'read', 'Read'

    alert = models.ForeignKey(
        EmergencyAlert,
        on_delete=models.CASCADE,
        related_name='deliveries',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alert_deliveries',
    )
    channel = models.CharField(max_length=10, choices=AlertChannel.choices)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    external_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alert_delivery'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert', 'user', 'channel'], name='delivery_alert_user_ch_idx'),
            models.Index(fields=['status', 'created_at'], name='delivery_status_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['alert', 'user', 'channel'],
                name='delivery_unique_per_channel',
            ),
        ]

    def __str__(self):
        return f'{self.alert.title} -> {self.user.username} via {self.channel}'


class AlertPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alert_preferences',
    )
    receive_in_app = models.BooleanField(default=True)
    receive_email = models.BooleanField(default=True)
    receive_sms = models.BooleanField(default=False)
    receive_push = models.BooleanField(default=True)
    min_severity = models.CharField(
        max_length=15,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
        help_text='Minimum severity to receive notifications',
    )
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} preferences'


class AlertTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject_template = models.CharField(max_length=200, blank=True)
    message_template = models.TextField()
    default_severity = models.CharField(
        max_length=15,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
    )
    default_channels = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'alert_template'
        ordering = ['name']

    def __str__(self):
        return self.name