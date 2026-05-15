from django.urls import path
from . import views

urlpatterns = [
    path('open/',                    views.open_dispute,    name='open_dispute'),
    path('evidence/',                views.submit_evidence, name='submit_evidence'),
    path('status/<str:dispute_id>/', views.dispute_status,  name='dispute_status'),
    path('admin/resolve/',           views.admin_resolve,   name='admin_resolve'),
]
