from django.urls import path
from . import views

urlpatterns = [
    path('initiate/',        views.initiate_payment, name='pay-initiate'),
    path('callbacks/mpesa/', views.mpesa_callback,   name='mpesa-callback'),
    path('direct-stk/',      views.direct_stk_push,  name='direct-stk-push'),
]
