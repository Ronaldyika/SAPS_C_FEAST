from django import forms
from .models import Attendee

class ConcertRegistrationForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['name', 'role', 'email', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }