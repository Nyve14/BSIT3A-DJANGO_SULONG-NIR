from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models

User = get_user_model()


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbldepartment'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('administrator', 'Administrator'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('member', 'Member'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?[0-9\s-]{7,20}$', message='Enter a valid phone number.')],
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        related_name='members',
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tbluserprofile'
        ordering = ['user__username']

    def __str__(self):
        return self.user.get_full_name() or self.user.username
