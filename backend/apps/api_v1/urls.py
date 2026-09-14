from django.urls import path
from . import views

urlpatterns = [
    path('cases/', views.list_cases_api, name='v1-list-cases'),
    path('cases/create/', views.create_case_api, name='v1-create-case'),
    path('cases/<str:case_id>/', views.case_detail_api, name='v1-case-detail'),
]