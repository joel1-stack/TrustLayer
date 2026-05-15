from django.urls import path
from . import views

urlpatterns = [
    path('create/',                    views.create_session,   name='session-create'),
    path('validate/<path:token>/',      views.validate_session, name='session-validate'),
    path('consume/<path:token>/',       views.consume_session,  name='session-consume'),
]
