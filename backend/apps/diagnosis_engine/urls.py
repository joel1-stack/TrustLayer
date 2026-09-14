from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiagnosisRecordViewSet

router = DefaultRouter()
router.register(r'diagnosis-records', DiagnosisRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
