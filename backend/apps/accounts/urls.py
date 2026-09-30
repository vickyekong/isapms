from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AuditLogViewSet,
    LoginView,
    LogoutView,
    MeView,
    NotificationViewSet,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    SystemSettingViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("settings", SystemSettingViewSet, basename="setting")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
