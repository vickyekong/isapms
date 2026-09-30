from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.audit import write_audit
from apps.accounts.permissions import IsAdminOrLecturer, IsAdministrator
from apps.academics.models import Enrolment
from apps.records.models import Assessment, Attendance, Result
from apps.records.serializers import AssessmentSerializer, AttendanceSerializer, ResultSerializer
from apps.records.services import ScoreError, apply_assessment, lecturer_can_access_course, scoped_enrolments


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    filterset_fields = ["enrolment", "date", "status"]
    search_fields = ["enrolment__student__matric_number", "enrolment__student__surname", "enrolment__course__code"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        enrolments = scoped_enrolments(self.request.user)
        query = Attendance.objects.filter(enrolment__in=enrolments).select_related(
            "enrolment__student", "enrolment__course"
        )
        course = self.request.query_params.get("course")
        if course:
            query = query.filter(enrolment__course_id=course)
        return query

    def get_permissions(self):
        if self.action in {"list", "retrieve", "summary"}:
            return [IsAuthenticated()]
        return [IsAdminOrLecturer()]

    def perform_create(self, serializer):
        enrolment = serializer.validated_data["enrolment"]
        if not lecturer_can_access_course(self.request.user, enrolment.course_id) and self.request.user.role != "admin":
            raise PermissionDenied("You can only record attendance for assigned courses.")
        attendance = serializer.save(marked_by=self.request.user)
        write_audit(self.request.user, "create", "Attendance", attendance.id, "Recorded attendance.", request=self.request)

    def perform_update(self, serializer):
        enrolment = serializer.instance.enrolment
        if not lecturer_can_access_course(self.request.user, enrolment.course_id):
            raise PermissionDenied("You can only update attendance for assigned courses.")
        attendance = serializer.save(marked_by=self.request.user)
        write_audit(self.request.user, "update", "Attendance", attendance.id, "Updated attendance.", request=self.request)

    @action(detail=False, methods=["post"])
    def mark(self, request):
        course_id = request.data.get("course")
        date = request.data.get("date")
        records = request.data.get("records") or []
        if not course_id or not date or not isinstance(records, list):
            raise ValidationError("Provide a course, date, and attendance records.")
        if not lecturer_can_access_course(request.user, course_id):
            raise PermissionDenied("You can only record attendance for assigned courses.")
        saved = []
        for record in records:
            enrolment = Enrolment.objects.filter(
                id=record.get("enrolment"), course_id=course_id, is_deleted=False, status="enrolled"
            ).first()
            if enrolment is None and record.get("student"):
                enrolment = Enrolment.objects.filter(
                    student_id=record.get("student"), course_id=course_id, is_deleted=False, status="enrolled"
                ).first()
            if enrolment is None:
                raise ValidationError("One or more students are not enrolled in this course.")
            if record.get("status") not in {"present", "absent", "excused"}:
                raise ValidationError("Attendance status must be present, absent, or excused.")
            attendance, _created = Attendance.objects.update_or_create(
                enrolment=enrolment,
                date=date,
                defaults={"status": record["status"], "marked_by": request.user},
            )
            saved.append(attendance)
        write_audit(request.user, "mark", "Attendance", course_id, f"Marked attendance for {len(saved)} students on {date}.", request=request)
        return Response(AttendanceSerializer(saved, many=True).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        course_id = request.query_params.get("course")
        enrolments = scoped_enrolments(request.user).filter(status="enrolled")
        if course_id:
            enrolments = enrolments.filter(course_id=course_id)
        rows = []
        for enrolment in enrolments.select_related("student", "course"):
            from apps.records.services import attendance_stats

            stats = attendance_stats(enrolment)
            rows.append(
                {
                    "enrolment": enrolment.id,
                    "student": enrolment.student_id,
                    "student_name": enrolment.student.full_name,
                    "matric_number": enrolment.student.matric_number,
                    "course": enrolment.course.code,
                    **stats,
                }
            )
        return Response(rows)


class AssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentSerializer
    filterset_fields = ["enrolment"]
    search_fields = ["enrolment__student__matric_number", "enrolment__course__code"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        enrolments = scoped_enrolments(self.request.user)
        query = Assessment.objects.filter(enrolment__in=enrolments).select_related(
            "enrolment__student", "enrolment__course", "result"
        )
        course = self.request.query_params.get("course")
        if course:
            query = query.filter(enrolment__course_id=course)
        return query

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsAdminOrLecturer()]

    def _save_scores(self, enrolment, ca_score, exam_score):
        if not lecturer_can_access_course(self.request.user, enrolment.course_id):
            raise PermissionDenied("You can only upload scores for assigned courses.")
        try:
            assessment, result = apply_assessment(enrolment, ca_score, exam_score, self.request.user)
        except ScoreError as exc:
            raise ValidationError(exc.message)
        return assessment, result

    def create(self, request, *args, **kwargs):
        enrolment = Enrolment.objects.filter(pk=request.data.get("enrolment"), is_deleted=False).first()
        if enrolment is None:
            raise ValidationError({"enrolment": "Select a valid enrolment."})
        assessment, _result = self._save_scores(enrolment, request.data.get("ca_score"), request.data.get("exam_score"))
        write_audit(request.user, "score", "Assessment", assessment.id, f"Saved scores for {enrolment.student.matric_number}.", request=request)
        return Response(self.get_serializer(assessment).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        assessment = self.get_object()
        ca_score = request.data.get("ca_score", assessment.ca_score)
        exam_score = request.data.get("exam_score", assessment.exam_score)
        assessment, _result = self._save_scores(assessment.enrolment, ca_score, exam_score)
        write_audit(request.user, "score", "Assessment", assessment.id, "Updated scores.", request=request)
        return Response(self.get_serializer(assessment).data)

    @action(detail=False, methods=["post"])
    def upload(self, request):
        course_id = request.data.get("course")
        scores = request.data.get("scores") or []
        if not course_id or not isinstance(scores, list):
            raise ValidationError("Provide a course and a list of scores.")
        if not lecturer_can_access_course(request.user, course_id):
            raise PermissionDenied("You can only upload scores for assigned courses.")
        saved = []
        for row in scores:
            enrolment = Enrolment.objects.filter(id=row.get("enrolment"), course_id=course_id, is_deleted=False).first()
            if enrolment is None and row.get("student"):
                enrolment = Enrolment.objects.filter(student_id=row.get("student"), course_id=course_id, is_deleted=False).first()
            if enrolment is None:
                raise ValidationError("One or more students are not enrolled in this course.")
            try:
                assessment, _result = apply_assessment(enrolment, row.get("ca_score"), row.get("exam_score"), request.user)
            except ScoreError as exc:
                raise ValidationError(exc.message)
            saved.append(assessment)
        write_audit(request.user, "upload", "Assessment", course_id, f"Uploaded scores for {len(saved)} students.", request=request)
        return Response(AssessmentSerializer(saved, many=True).data)


class ResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResultSerializer
    filterset_fields = ["grade", "is_validated", "is_locked"]
    search_fields = ["enrolment__student__matric_number", "enrolment__student__surname", "enrolment__course__code", "grade"]

    def get_queryset(self):
        enrolments = scoped_enrolments(self.request.user)
        query = Result.objects.filter(enrolment__in=enrolments).select_related(
            "enrolment__student__faculty",
            "enrolment__student__department",
            "enrolment__course",
            "enrolment__session",
            "enrolment__semester",
            "assessment",
        )
        params = self.request.query_params
        if params.get("session"):
            query = query.filter(enrolment__session_id=params.get("session"))
        if params.get("semester"):
            query = query.filter(enrolment__semester_id=params.get("semester"))
        if params.get("faculty"):
            query = query.filter(enrolment__student__faculty_id=params.get("faculty"))
        if params.get("department"):
            query = query.filter(enrolment__student__department_id=params.get("department"))
        if params.get("level"):
            query = query.filter(enrolment__student__level=params.get("level"))
        if params.get("course"):
            query = query.filter(enrolment__course_id=params.get("course"))
        if params.get("student"):
            query = query.filter(enrolment__student_id=params.get("student"))
        return query

    @action(detail=True, methods=["post"], permission_classes=[IsAdministrator])
    def lock(self, request, pk=None):
        result = self.get_object()
        result.is_locked = True
        result.save(update_fields=["is_locked", "updated_at"])
        write_audit(request.user, "lock", "Result", result.id, f"Locked result {result.enrolment.course.code}.", request=request)
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdministrator])
    def unlock(self, request, pk=None):
        result = self.get_object()
        result.is_locked = False
        result.save(update_fields=["is_locked", "updated_at"])
        write_audit(request.user, "unlock", "Result", result.id, f"Unlocked result {result.enrolment.course.code}.", request=request)
        return Response(self.get_serializer(result).data)
