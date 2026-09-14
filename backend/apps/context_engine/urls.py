from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContextRecordViewSet

router = DefaultRouter()
router.register(r'context-records', ContextRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
