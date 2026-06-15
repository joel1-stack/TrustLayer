from django.urls import path
from django.shortcuts import render
from . import views

urlpatterns = [
    path('', views.index, name='portal-index'),
    path('register/', views.register_ajax, name='portal-register-ajax'),
    path('login/', views.login_ajax, name='portal-login-ajax'),
]
