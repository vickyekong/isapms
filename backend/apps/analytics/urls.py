from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.analytics.views import DashboardView, PredictionViewSet, ReportView

router = DefaultRouter()
router.register("predictions", PredictionViewSet, basename="prediction")

urlpatterns = router.urls + [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("reports/", ReportView.as_view(), name="reports"),
]
