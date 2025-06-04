from django.urls import path
from . import views

urlpatterns = [
    path('', views.concert_registration_view, name='index'),
]
