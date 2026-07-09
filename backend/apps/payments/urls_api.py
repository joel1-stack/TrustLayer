from django.urls import path
from . import views

urlpatterns = [
    path('link/', views.generate_payment_link, name='generate-payment-link'),
]