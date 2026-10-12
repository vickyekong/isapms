from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        payload = {"status": "ok", "service": "isapms", "demo": settings.DEMO_MODE}
        if settings.DEMO_MODE:
            from apps.accounts.management.commands.seed_sample_data import SAMPLE_DOMAIN, SAMPLE_PASSWORD

            payload["demo_password"] = SAMPLE_PASSWORD
            payload["demo_accounts"] = [
                {"role": "Administrator", "identifier": f"sample.admin@{SAMPLE_DOMAIN}"},
                {"role": "Lecturer", "identifier": f"sample.lecturer01@{SAMPLE_DOMAIN}"},
                {"role": "Student", "identifier": f"sample.student001@{SAMPLE_DOMAIN}"},
            ]
        return Response(payload)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.academics.urls")),
    path("api/v1/", include("apps.analytics.urls")),
]

admin.site.site_header = "ISAPMS administration"
admin.site.site_title = "ISAPMS"
