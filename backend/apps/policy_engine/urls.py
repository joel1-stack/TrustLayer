from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PolicyRuleViewSet, PolicyDecisionViewSet

router = DefaultRouter()
router.register(r'policy-rules', PolicyRuleViewSet)
router.register(r'policy-decisions', PolicyDecisionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
