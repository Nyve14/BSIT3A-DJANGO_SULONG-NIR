from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.users.models import Department

from .models import ConcernCategory, ConcernReport, GeographicArea

User = get_user_model()


class ConcernReportForm(forms.ModelForm):
    class Meta:
        model = ConcernReport
        fields = [
            'subject',
            'description',
            'category',
            'area',
            'location_details',
            'latitude',
            'longitude',
        ]
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 200,
                'placeholder': 'Briefly describe the concern',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe what happened and how it affects the community',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'location_details': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 255,
                'placeholder': 'Barangay, street, landmark, or nearby location',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
        labels = {
            'area': 'City, municipality, or barangay',
            'location_details': 'Specific location',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ConcernCategory.objects.filter(
            is_active=True,
        )
        self.fields['area'].queryset = GeographicArea.objects.filter(
            is_active=True,
        ).exclude(level=GeographicArea.Level.REGION)

class ConcernUpdateForm(forms.Form):
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share an update or add a note',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Keep current status')] + list(ConcernReport.Status.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    department = forms.ModelChoiceField(
        required=False,
        queryset=Department.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    assigned_to = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Assigned staff member',
    )
    staff_only = forms.BooleanField(
        required=False,
        label='Staff-only note',
    )

    def __init__(self, *args, is_staff=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_staff:
            self.fields['status'].choices = ConcernReport.Status.choices
            self.fields['department'].queryset = Department.objects.order_by('name')
            self.fields['assigned_to'].queryset = User.objects.filter(
                Q(is_staff=True) | Q(is_superuser=True),
                is_active=True,
            ).order_by('username')
        else:
            del self.fields['status']
            del self.fields['department']
            del self.fields['assigned_to']
            del self.fields['staff_only']
