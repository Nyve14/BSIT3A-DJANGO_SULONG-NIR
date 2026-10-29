from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import ConcernCategory, ConcernReport, GeographicArea

User = get_user_model()


class ConcernReportForm(forms.ModelForm):
    province = forms.ModelChoiceField(
        queryset=GeographicArea.objects.filter(level=GeographicArea.Level.PROVINCE, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_province'}),
        label='Province'
    )
    city_municipality = forms.ModelChoiceField(
        queryset=GeographicArea.objects.filter(level=GeographicArea.Level.CITY_MUNICIPALITY, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_city_municipality'}),
        label='City/Municipality'
    )

    class Meta:
        model = ConcernReport
        fields = [
            'subject',
            'description',
            'category',
            'province',
            'city_municipality',
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
            'area': forms.Select(attrs={'class': 'form-select', 'id': 'id_barangay'}),
            'location_details': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 255,
                'placeholder': 'Barangay, street, landmark, or nearby location',
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
        labels = {
            'area': 'Barangay (optional)',
            'location_details': 'Specific location',
        }

    def __init__(self, *args, emergency_mode=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ConcernCategory.objects.filter(
            is_active=True,
        )
        if emergency_mode:
            public_safety = self.fields['category'].queryset.filter(
                name='Public Safety',
            )
            self.fields['category'].queryset = public_safety
            self.fields['category'].label = 'Emergency type'
            self.fields['subject'].label = 'Emergency title'
            self.fields['subject'].widget.attrs['placeholder'] = (
                'Example: Traffic accident on the main road'
            )
            self.fields['description'].label = 'What happened and what help is needed?'
            self.fields['description'].widget.attrs['placeholder'] = (
                'Describe the accident, danger, injuries, or urgent assistance needed'
            )
            self.fields['location_details'].label = 'Exact emergency location'
            self.fields['location_details'].widget.attrs['placeholder'] = (
                'Street, landmark, barangay, or nearest location'
            )
        self.fields['area'].required = False
        
        # If we have an instance (editing), set initial values for province and city
        if self.instance.pk and self.instance.area:
            area = self.instance.area
            if area.level == GeographicArea.Level.BARANGAY:
                self.initial['city_municipality'] = area.parent_id
                if area.parent and area.parent.parent:
                    self.initial['province'] = area.parent.parent_id
            elif area.level == GeographicArea.Level.CITY_MUNICIPALITY:
                self.initial['city_municipality'] = area.pk
                if area.parent:
                    self.initial['province'] = area.parent_id
            elif area.level == GeographicArea.Level.PROVINCE:
                self.initial['province'] = area.pk

        # Filter querysets based on selections if data is present
        if 'province' in self.data:
            try:
                province_id = int(self.data.get('province'))
                self.fields['city_municipality'].queryset = GeographicArea.objects.filter(
                    parent_id=province_id, level=GeographicArea.Level.CITY_MUNICIPALITY, is_active=True
                )
            except (ValueError, TypeError):
                self.fields['city_municipality'].queryset = GeographicArea.objects.none()
        
        if 'city_municipality' in self.data:
            try:
                city_id = int(self.data.get('city_municipality'))
                self.fields['area'].queryset = GeographicArea.objects.filter(
                    parent_id=city_id, level=GeographicArea.Level.BARANGAY, is_active=True
                )
            except (ValueError, TypeError):
                self.fields['area'].queryset = GeographicArea.objects.none()
        elif self.instance.pk and self.instance.area:
             # Handle editing initial state
             pass
        else:
             self.fields['area'].queryset = GeographicArea.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        province = cleaned_data.get('province')
        city = cleaned_data.get('city_municipality')
        barangay = cleaned_data.get('area')

        # Determine the most specific area selected
        final_area = barangay or city or province

        if not final_area:
            self.add_error('province', 'Please select at least a province.')
        
        cleaned_data['area'] = final_area
        return cleaned_data

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
            self.fields['assigned_to'].queryset = User.objects.filter(
                Q(is_staff=True) | Q(is_superuser=True),
                is_active=True,
            ).order_by('username')
        else:
            del self.fields['status']
            del self.fields['assigned_to']
            del self.fields['staff_only']
