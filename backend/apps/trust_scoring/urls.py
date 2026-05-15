from django.urls import path
from . import views

urlpatterns = [
    path('my-score/',                    views.my_trust_score,     name='my_trust_score'),
    path('merchant/<str:merchant_key>/', views.public_trust_score, name='public_trust_score'),
]
