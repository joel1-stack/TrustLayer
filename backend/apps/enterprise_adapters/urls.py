from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnterpriseAdapterViewSet

router = DefaultRouter()
router.register(r'enterprise-adapters', EnterpriseAdapterViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
