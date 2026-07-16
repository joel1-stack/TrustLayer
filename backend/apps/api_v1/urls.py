from django.urls import path
from . import views

urlpatterns = [
    path('agreements/', views.create_agreement, name='v1-create-agreement'),
]