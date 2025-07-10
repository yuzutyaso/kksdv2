# commands/urls.py
from django.urls import path
from . import views

app_name = 'commands'

urlpatterns = [
    path('process/', views.process_command, name='process_command'),
]
