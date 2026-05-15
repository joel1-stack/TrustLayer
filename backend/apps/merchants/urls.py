from django.urls import path
from . import views

urlpatterns = [
    path('register/',         views.register_merchant, name='merchant-register'),
    path('login/',            views.login_merchant,    name='merchant-login'),
    path('profile/',          views.merchant_profile,  name='merchant-profile'),
    path('keys/regenerate/',  views.regenerate_keys,   name='merchant-regenerate-keys'),
]
