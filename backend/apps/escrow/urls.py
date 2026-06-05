from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.deals_list,         name='deals-list'),
    path('<str:deal_code>/',                    views.deal_status,        name='deal-status'),
    path('<str:deal_code>/confirm/',            views.buyer_confirm,      name='buyer-confirm'),
    path('<str:deal_code>/seller-deliver/',     views.seller_deliver,     name='seller-deliver'),
    path('<str:deal_code>/dispute/',            views.raise_dispute,      name='raise-dispute'),
]
