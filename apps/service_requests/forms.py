from django import forms

from .models import ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['subject', 'description', 'location', 'request_type', 'priority']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Barangay certificate for school enrollment',
                'maxlength': 200,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Explain the purpose and include details needed to process your request',
            }),
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a barangay, street, or landmark',
                'maxlength': 255,
            }),
        }
        labels = {
            'subject': 'Request title',
            'description': 'Purpose and details',
            'request_type': 'Request type',
            'location': 'Location / Barangay',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].help_text = (
            'For document requests, include the purpose and any details needed to process it.'
        )
