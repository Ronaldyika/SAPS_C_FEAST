from django import forms
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Attendee


class ConcertRegistrationForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['name', 'role', 'email', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'title': 'Upload a passport-sized photo (max 700x700 pixels)'
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if image:
            img = Image.open(image)
            width, height = img.size

            if width > 2600 or height > 4000:
                raise forms.ValidationError("Image must be no larger than 1000x1000 pixels.")

            # Optional: Resize image to 600x600 if needed
            img = img.resize((600, 600))
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            image = InMemoryUploadedFile(
                buffer, 'ImageField', image.name, 'image/png', buffer.tell(), None
            )

        return image
