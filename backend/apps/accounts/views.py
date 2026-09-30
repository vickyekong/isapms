from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.audit import write_audit
from apps.accounts.models import AuditLog, Notification, SystemSetting, User
from apps.accounts.permissions import IsAdministrator
from apps.accounts.serializers import (
    AuditLogSerializer,
    NotificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SystemSettingSerializer,
    UserSerializer,
)
from apps.accounts.services import ensure_default_settings


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        identifier = str(request.data.get("identifier") or request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        user = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(username__iexact=identifier).first()
        if user is None:
            from apps.academics.models import Lecturer, Student

            student = Student.objects.filter(matric_number__iexact=identifier).select_related("user").first()
            lecturer = Lecturer.objects.filter(staff_id__iexact=identifier).select_related("user").first()
            user = (student.user if student else None) or (lecturer.user if lecturer else None)
        if user is None or not user.check_password(password):
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "This account has been deactivated."}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email
        write_audit(user, "login", "User", user.id, f"{user.email} signed in.", request=request)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            }
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            raise ValidationError({"refresh": "Refresh token is required."})
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Refresh token is invalid or expired."})
        write_audit(request.user, "logout", "User", request.user.id, f"{request.user.email} signed out.", request=request)
        return Response({"detail": "Signed out."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        payload = {"detail": "If an account exists for that email, password reset instructions have been sent."}
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            site = settings.FRONTEND_URL or request.build_absolute_uri("/").rstrip("/")
            link = f"{site}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Reset your ISAPMS password",
                f"Use this link to choose a new password:\n{link}\n\nIf you did not request this, you can ignore the message.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            if settings.DEBUG:
                payload["debug_reset_url"] = link
        return Response(payload)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise ValidationError({"uid": "This reset link is invalid."})
        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            raise ValidationError({"token": "This reset link is invalid or has expired."})
        validate_password(serializer.validated_data["password"], user)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        write_audit(user, "password_reset", "User", user.id, "Password was reset.", request=request)
        return Response({"detail": "Password updated. You can sign in with the new password."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserSerializer(request.user).data
        student = getattr(request.user, "student_profile", None)
        lecturer = getattr(request.user, "lecturer_profile", None)
        if student:
            data["student_id"] = student.id
            data["matric_number"] = student.matric_number
        if lecturer:
            data["lecturer_id"] = lecturer.id
            data["staff_id"] = lecturer.staff_id
        return Response(data)

    def patch(self, request):
        allowed = {"first_name", "last_name", "phone"}
        payload = {key: value for key, value in request.data.items() if key in allowed}
        serializer = UserSerializer(request.user, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("last_name", "first_name")
    serializer_class = UserSerializer
    permission_classes = [IsAdministrator]
    search_fields = ["email", "username", "first_name", "last_name", "phone"]
    filterset_fields = ["role", "is_active", "is_sample"]
    ordering_fields = ["last_name", "email", "created_at", "role"]

    def perform_create(self, serializer):
        user = serializer.save()
        write_audit(self.request.user, "create", "User", user.id, f"Created {user.role} account {user.email}.", request=self.request)

    def perform_update(self, serializer):
        user = serializer.save()
        write_audit(self.request.user, "update", "User", user.id, f"Updated account {user.email}.", request=self.request)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            raise PermissionDenied("You cannot deactivate your own account from this action.")
        user.is_active = False
        user.save(update_fields=["is_active"])
        write_audit(request.user, "deactivate", "User", user.id, f"Deactivated {user.email}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        write_audit(request.user, "activate", "User", user.id, f"Activated {user.email}.", request=request)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            raise PermissionDenied("You cannot deactivate your own account.")
        user.is_active = False
        user.save(update_fields=["is_active"])
        write_audit(request.user, "deactivate", "User", user.id, f"Deactivated {user.email}.", request=request)
        return Response(UserSerializer(user).data)


class NotificationViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = bool(request.data.get("is_read", True))
        notification.save(update_fields=["is_read"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"detail": "Notifications marked as read."})


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdministrator]
    search_fields = ["description", "entity", "action"]
    filterset_fields = ["action", "entity"]


class SystemSettingViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdministrator]
    lookup_field = "key"

    def get_queryset(self):
        ensure_default_settings()
        return SystemSetting.objects.all()

    def partial_update(self, request, *args, **kwargs):
        setting = self.get_object()
        serializer = self.get_serializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        write_audit(
            request.user,
            "update",
            "SystemSetting",
            setting.key,
            f"Updated setting {setting.key}.",
            metadata={"value": serializer.data.get("value")},
            request=request,
        )
        return Response(serializer.data)
