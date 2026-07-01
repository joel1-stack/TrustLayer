from django.urls import path
from . import views, views_flow

urlpatterns = [
    path('initiate/',            views.initiate_payment,  name='pay-initiate'),
    path('callbacks/mpesa/',     views.mpesa_callback,    name='mpesa-callback'),
    path('callbacks/b2c/result/', views.mpesa_b2c_result, name='mpesa-b2c-result'),
    path('callbacks/b2c/timeout/', views.mpesa_b2c_timeout, name='mpesa-b2c-timeout'),
    path('direct-stk/',          views.direct_stk_push,   name='direct-stk-push'),

    # IntaSend flow endpoints
    path('webhooks/intasend/',   views_flow.intasend_callback, name='intasend-webhook'),
    path('flow/collect/',        views_flow.trigger_collect,   name='flow-collect'),
    path('flow/payout/',         views_flow.trigger_payout,    name='flow-payout'),
    path('flow/wallet/',         views_flow.check_wallet,      name='flow-wallet'),
    path('flow/full/',           views_flow.full_flow,         name='flow-full'),
]
