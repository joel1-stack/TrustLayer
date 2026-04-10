from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("create-deal/", TemplateView.as_view(template_name="create_deal.html"), name="create-deal"),
    path("pay-mpesa/", TemplateView.as_view(template_name="pay_mpesa.html"), name="pay-mpesa"),
    path("deal-status/", TemplateView.as_view(template_name="deal_status.html"), name="deal-status"),
]
