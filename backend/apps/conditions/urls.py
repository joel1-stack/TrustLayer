from django.urls import path
from . import views

urlpatterns = [
    path('', views.add_condition, name='add-condition'),
    path('<str:condition_id>/met/', views.mark_condition_met, name='mark-condition-met'),
    path('agreement/<str:agreement_id>/', views.get_conditions, name='get-conditions'),
]