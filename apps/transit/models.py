import uuid

from django.conf import settings
from django.db import models


class TransitAgency(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transit_agency'
        ordering = ['name']

    def __str__(self):
        return self.name


class TransitRoute(models.Model):
    class VehicleType(models.TextChoices):
        BUS = 'bus', 'Bus'
        JEEPNEY = 'jeepney', 'Jeepney'
        MULTICAB = 'multicab', 'Multicab'
        TRICYCLE = 'tricycle', 'Tricycle'
        FERRY = 'ferry', 'Ferry'
        OTHER = 'other', 'Other'

    agency = models.ForeignKey(
        TransitAgency,
        on_delete=models.PROTECT,
        related_name='routes',
    )
    short_name = models.CharField(max_length=50, help_text='e.g., "Bacolod - Dumaguete"')
    long_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BUS,
    )
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Hex color for map display')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transit_route'
        ordering = ['short_name']

    def __str__(self):
        return f'{self.short_name} ({self.agency.short_name})'


class TransitStop(models.Model):
    route = models.ForeignKey(
        TransitRoute,
        on_delete=models.CASCADE,
        related_name='stops',
    )
    name = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    sequence = models.PositiveSmallIntegerField()
    stop_type = models.CharField(
        max_length=20,
        choices=[
            ('regular', 'Regular Stop'),
            ('terminal', 'Terminal'),
            ('major', 'Major Stop'),
        ],
        default='regular',
    )
    estimated_time_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='Estimated travel time from previous stop in minutes',
    )
    landmarks = models.TextField(blank=True, help_text='Nearby landmarks for identification')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'transit_stop'
        ordering = ['route', 'sequence']
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'sequence'],
                name='transit_stop_route_seq_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.route.short_name})'


class TransitSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    route = models.ForeignKey(
        TransitRoute,
        on_delete=models.CASCADE,
        related_name='schedules',
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    departure_time = models.TimeField()
    origin_stop = models.ForeignKey(
        TransitStop,
        on_delete=models.CASCADE,
        related_name='departing_schedules',
    )
    destination_stop = models.ForeignKey(
        TransitStop,
        on_delete=models.CASCADE,
        related_name='arriving_schedules',
    )
    estimated_duration_minutes = models.PositiveSmallIntegerField()
    frequency_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='If regular frequency, minutes between departures',
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'transit_schedule'
        ordering = ['day_of_week', 'departure_time']
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'day_of_week', 'departure_time', 'origin_stop'],
                name='transit_schedule_unique',
            ),
        ]

    def __str__(self):
        return f'{self.route.short_name} - {self.get_day_of_week_display()} {self.departure_time}'


class TransitAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'

    route = models.ForeignKey(
        TransitRoute,
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
    )
    agency = models.ForeignKey(
        TransitAgency,
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='transit_alerts_created',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transit_alert'
        ordering = ['-starts_at']

    def __str__(self):
        return f'{self.title} ({self.get_severity_display()})'