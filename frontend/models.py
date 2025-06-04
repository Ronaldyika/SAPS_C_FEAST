from django.db import models

class Attendee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    role = models.CharField(max_length=100)
    image = models.ImageField(upload_to='attendee_images/')
    generated_flyer = models.ImageField(upload_to='generated_flyers/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name