from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActionPlanViewSet, ActionResultViewSet

router = DefaultRouter()
router.register(r'action-plans', ActionPlanViewSet)
router.register(r'action-results', ActionResultViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
