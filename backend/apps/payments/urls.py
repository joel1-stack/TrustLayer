from django.urls import path
from . import views

urlpatterns = [
    path('initiate/',            views.initiate_payment,  name='pay-initiate'),
    path('callbacks/mpesa/',     views.mpesa_callback,    name='mpesa-callback'),
    path('callbacks/b2c/result/', views.mpesa_b2c_result, name='mpesa-b2c-result'),
    path('callbacks/b2c/timeout/', views.mpesa_b2c_timeout, name='mpesa-b2c-timeout'),
    path('direct-stk/',          views.direct_stk_push,   name='direct-stk-push'),
]
