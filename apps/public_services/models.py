import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def category_slugify(instance, name):
    """Generate a unique slug for a service category."""
    base = slugify(name)
    slug = base
    n = 1
    while ServiceCategory.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


class ServiceCategory(models.Model):
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        related_name='children',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=220, blank=True, help_text='URL-friendly identifier (auto-generated from name)')
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='FontAwesome icon class, e.g., fas fa-hospital')
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'service_category'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'service categories'
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'name'],
                name='service_category_parent_name_uniq',
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = category_slugify(self, self.name)
        super().save(*args, **kwargs)


class Service(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        TEMPORARILY_CLOSED = 'temporarily_closed', 'Temporarily Closed'

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
    )
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    barangay = models.ForeignKey(
        'concerns.GeographicArea',
        on_delete=models.SET_NULL,
        related_name='services',
        null=True,
        blank=True,
        limit_choices_to={'level': 'barangay'},
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    hours_monday = models.CharField(max_length=100, blank=True, default='8:00 AM - 5:00 PM')
    hours_tuesday = models.CharField(max_length=100, blank=True, default='8:00 AM - 5:00 PM')
    hours_wednesday = models.CharField(max_length=100, blank=True, default='8:00 AM - 5:00 PM')
    hours_thursday = models.CharField(max_length=100, blank=True, default='8:00 AM - 5:00 PM')
    hours_friday = models.CharField(max_length=100, blank=True, default='8:00 AM - 5:00 PM')
    hours_saturday = models.CharField(max_length=100, blank=True, default='Closed')
    hours_sunday = models.CharField(max_length=100, blank=True, default='Closed')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_services',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'service'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category', 'status'], name='svc_cat_status_idx'),
            models.Index(fields=['barangay', 'status'], name='svc_brgy_status_idx'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            self.slug = base
            n = 1
            while Service.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base}-{n}'
                n += 1
        super().save(*args, **kwargs)

    def get_hours_for_day(self, day):
        """Return hours for a given day (0=Monday, 6=Sunday)."""
        hours_map = {
            0: self.hours_monday,
            1: self.hours_tuesday,
            2: self.hours_wednesday,
            3: self.hours_thursday,
            4: self.hours_friday,
            5: self.hours_saturday,
            6: self.hours_sunday,
        }
        return hours_map.get(day, '')

    def hours_today(self):
        """Return today's operating hours in the project timezone."""
        from django.utils import timezone
        return self.get_hours_for_day(timezone.localtime().weekday())

    def is_open_now(self):
        """Check if service is currently open based on local time."""
        from django.utils import timezone
        try:
            now = timezone.localtime()
            day = now.weekday()  # 0=Monday
            hours = self.get_hours_for_day(day)
            if not hours or hours.lower() == 'closed':
                return False
            # Parse hours like "8:00 AM - 5:00 PM"
            import re
            match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)', hours)
            if not match:
                return True  # Assume open if can't parse
            open_h, open_m, open_ampm, close_h, close_m, close_ampm = match.groups()
            open_hour = int(open_h) + (12 if open_ampm == 'PM' and int(open_h) != 12 else 0)
            close_hour = int(close_h) + (12 if close_ampm == 'PM' and int(close_h) != 12 else 0)
            if open_ampm == 'AM' and int(open_h) == 12:
                open_hour = 0
            if close_ampm == 'AM' and int(close_h) == 12:
                close_hour = 0
            current_min = now.hour * 60 + now.minute
            return open_hour * 60 + int(open_m) <= current_min <= close_hour * 60 + int(close_m)
        except Exception:
            return True


class ServiceReview(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_reviews',
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'service_review'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'user'],
                name='service_review_unique',
            ),
        ]

    def __str__(self):
        return f'{self.service.name} - {self.rating}/5 by {self.user.username}'