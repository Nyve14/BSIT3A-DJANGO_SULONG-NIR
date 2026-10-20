from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Service, ServiceCategory, ServiceReview

User = get_user_model()


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'name',
            'category',
            'description',
            'address',
            'barangay',
            'latitude',
            'longitude',
            'phone',
            'email',
            'website',
            'hours_monday',
            'hours_tuesday',
            'hours_wednesday',
            'hours_thursday',
            'hours_friday',
            'hours_saturday',
            'hours_sunday',
            'status',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 200,
                'placeholder': 'Service name (e.g., Bacolod City Health Office)',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the services offered',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Complete address including street, barangay, city',
            }),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'e.g., 10.6407',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'e.g., 122.9557',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(034) 123-4567',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'office@example.gov.ph',
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.gov.ph',
            }),
            'hours_monday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '8:00 AM - 5:00 PM',
            }),
            'hours_tuesday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '8:00 AM - 5:00 PM',
            }),
            'hours_wednesday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '8:00 AM - 5:00 PM',
            }),
            'hours_thursday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '8:00 AM - 5:00 PM',
            }),
            'hours_friday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '8:00 AM - 5:00 PM',
            }),
            'hours_saturday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Closed',
            }),
            'hours_sunday': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Closed',
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'barangay': 'Barangay (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ServiceCategory.objects.filter(
            is_active=True,
            parent__isnull=True,
        )
        from apps.concerns.models import GeographicArea
        self.fields['barangay'].queryset = GeographicArea.objects.filter(
            is_active=True,
            level=GeographicArea.Level.BARANGAY,
        ).select_related('parent', 'parent__parent').order_by('parent__parent__name', 'parent__name', 'name')


class ServiceReviewForm(forms.ModelForm):
    class Meta:
        model = ServiceReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, '★' * i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Share your experience (optional)',
            }),
        }


class ServiceSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, address, or category...',
        }),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=ServiceCategory.objects.filter(is_active=True, parent__isnull=True),
        empty_label='All categories',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    barangay = forms.ModelChoiceField(
        required=False,
        queryset=None,  # Set in __init__
        empty_label='All barangays',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All statuses')] + list(Service.Status.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.concerns.models import GeographicArea
        self.fields['barangay'].queryset = GeographicArea.objects.filter(
            is_active=True,
            level=GeographicArea.Level.BARANGAY,
        ).select_related('parent', 'parent__parent').order_by('parent__parent__name', 'parent__name', 'name')