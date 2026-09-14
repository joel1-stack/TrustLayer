from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VerificationCheckViewSet, VerificationResultViewSet

router = DefaultRouter()
router.register(r'verification-checks', VerificationCheckViewSet)
router.register(r'verification-results', VerificationResultViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
