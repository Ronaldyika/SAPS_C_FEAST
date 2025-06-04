from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.concert_registration_view, name='index'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
