from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.concert_registration_view, name='index'),
    path('flyer/<int:pk>/', views.flyer_preview_view, name='flyer_preview'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
