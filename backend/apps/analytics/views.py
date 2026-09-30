from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.audit import write_audit
from apps.accounts.permissions import IsAdministrator
from apps.academics.models import Enrolment
from apps.analytics.engine import AnalyticsError, InsufficientDataError, predict_for_enrolment, train_model
from apps.analytics.insights import at_risk_alerts, build_dashboard
from apps.analytics.models import ModelVersion, Prediction
from apps.analytics.reports import REPORT_TYPES, render_report
from apps.analytics.serializers import ModelVersionSerializer, PredictionSerializer
from apps.records.services import lecturer_can_access_course, scoped_students


class PredictionRateThrottle(UserRateThrottle):
    scope = "prediction"


class PredictionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [PredictionRateThrottle]
    filterset_fields = ["student", "course", "risk_level", "predicted_grade", "data_status"]
    search_fields = ["student__matric_number", "student__surname", "course__code"]

    def get_queryset(self):
        query = Prediction.objects.select_related("student", "course", "model_version")
        user = self.request.user
        if not getattr(user, "is_authenticated", False):
            return query.none()
        if user.role == "student":
            student = getattr(user, "student_profile", None)
            return query.filter(student=student)
        if user.role == "lecturer":
            return query.filter(course__assignments__lecturer__user=user).distinct()
        return query

    def create(self, request, *args, **kwargs):
        if request.user.role not in {"admin", "lecturer"}:
            raise PermissionDenied("Only administrators and lecturers can run predictions.")
        student_id = request.data.get("student")
        course_id = request.data.get("course")
        students = scoped_students(request.user)
        student = students.filter(pk=student_id).first()
        if student is None:
            raise ValidationError({"student": "Select a student you are allowed to assess."})
        enrolments = Enrolment.objects.filter(student=student, is_deleted=False, status="enrolled")
        if course_id:
            enrolments = enrolments.filter(course_id=course_id)
            if request.user.role == "lecturer" and not lecturer_can_access_course(request.user, course_id):
                raise PermissionDenied("You can only run predictions for assigned courses.")
        enrolment = enrolments.select_related("student", "course", "session", "semester").first()
        if enrolment is None:
            raise ValidationError(
                "This student does not have enough academic records to generate a reliable prediction."
            )
        try:
            prediction = predict_for_enrolment(enrolment, actor=request.user, allow_partial=True)
        except InsufficientDataError as exc:
            raise ValidationError(exc.message)
        except AnalyticsError as exc:
            raise ValidationError(exc.message)
        write_audit(
            request.user,
            "predict",
            "Prediction",
            prediction.id,
            f"Predicted grade {prediction.predicted_grade} for {student.matric_number}.",
            request=request,
        )
        return Response(self.get_serializer(prediction).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="at-risk")
    def at_risk(self, request):
        if request.user.role == "student":
            raise PermissionDenied("At-risk monitoring is available to lecturers and administrators.")
        alerts = at_risk_alerts(request.user)
        risk = request.query_params.get("risk_level")
        if risk:
            alerts = [alert for alert in alerts if alert["risk_level"] == risk]
        course = request.query_params.get("course")
        if course:
            alerts = [
                alert
                for alert in alerts
                if (isinstance(alert.get("course"), dict) and str(alert["course"].get("id")) == str(course))
            ]
        return Response({"count": len(alerts), "results": alerts})

    @action(detail=False, methods=["post"], permission_classes=[IsAdministrator])
    def train(self, request):
        try:
            model_version = train_model(actor=request.user, sample=False)
        except AnalyticsError as exc:
            raise ValidationError(exc.message)
        write_audit(request.user, "train", "ModelVersion", model_version.id, f"Trained model {model_version.version}.", request=request)
        return Response(ModelVersionSerializer(model_version).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def model(self, request):
        if request.user.role == "student":
            raise PermissionDenied("Model metrics are available to lecturers and administrators.")
        versions = ModelVersion.objects.all()
        return Response(ModelVersionSerializer(versions, many=True).data)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_dashboard(request.user))


class ReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        report_type = request.query_params.get("type", "results")
        export_format = request.query_params.get("format", "csv").lower()
        if report_type not in REPORT_TYPES:
            raise ValidationError({"type": "Unknown report type."})
        if request.user.role == "student" and report_type not in {"student_performance", "attendance", "results"}:
            raise PermissionDenied("You can only download your own academic reports.")
        params = request.query_params.copy()
        if request.user.role == "student":
            student = getattr(request.user, "student_profile", None)
            if student is None:
                raise PermissionDenied("No student profile is linked to this account.")
            params["student"] = str(student.id)
        if export_format not in {"csv", "pdf", "xlsx", "excel"}:
            raise ValidationError({"format": "Choose csv, xlsx, or pdf."})
        try:
            return render_report(report_type, export_format, params, request.user)
        except ValueError as exc:
            raise ValidationError(str(exc))
