import csv
import io
import secrets

from django.db import IntegrityError, transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.audit import write_audit
from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrLecturer, IsAdministrator
from apps.academics.models import (
    AcademicSession,
    Course,
    CourseAssignment,
    Department,
    Enrolment,
    Faculty,
    Lecturer,
    Semester,
    Student,
)
from apps.academics.serializers import (
    AcademicSessionSerializer,
    CourseAssignmentSerializer,
    CourseSerializer,
    DepartmentSerializer,
    EnrolmentSerializer,
    FacultySerializer,
    LecturerSerializer,
    SemesterSerializer,
    StudentSerializer,
)
from apps.records.services import scoped_enrolments, scoped_students


def _temporary_password():
    return f"Tmp#{secrets.token_hex(4)}aA1"


def _sync_user(person, role, username, password=None):
    user = person.user
    if user is None:
        user = User.objects.create_user(
            email=person.email,
            username=username,
            password=password or _temporary_password(),
            first_name=person.first_name,
            last_name=person.surname,
            role=role,
            phone=getattr(person, "telephone", ""),
            is_sample=person.is_sample,
        )
        person.user = user
        person.save(update_fields=["user"])
        user.temporary_password = password or user.temporary_password if hasattr(user, "temporary_password") else password
        if password is None:
            user._generated_password = user.password
        return user
    user.email = person.email
    user.username = username
    user.first_name = person.first_name
    user.last_name = person.surname
    user.phone = getattr(person, "telephone", "")
    user.role = role
    if password:
        user.set_password(password)
    user.save()
    return user


class FacultyViewSet(viewsets.ModelViewSet):
    serializer_class = FacultySerializer
    permission_classes = [IsAdministrator]
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return Faculty.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        faculty = serializer.save()
        write_audit(self.request.user, "create", "Faculty", faculty.id, f"Created faculty {faculty.name}.", request=self.request)

    def perform_update(self, serializer):
        faculty = serializer.save()
        write_audit(self.request.user, "update", "Faculty", faculty.id, f"Updated faculty {faculty.name}.", request=self.request)

    def destroy(self, request, *args, **kwargs):
        faculty = self.get_object()
        faculty.soft_delete()
        faculty.is_active = False
        faculty.save(update_fields=["is_active", "updated_at"])
        write_audit(request.user, "delete", "Faculty", faculty.id, f"Archived faculty {faculty.name}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdministrator]
    search_fields = ["name", "code", "faculty__name"]
    filterset_fields = ["faculty", "is_active"]

    def get_queryset(self):
        return Department.objects.filter(is_deleted=False).select_related("faculty")

    def perform_create(self, serializer):
        department = serializer.save()
        write_audit(self.request.user, "create", "Department", department.id, f"Created department {department.name}.", request=self.request)

    def perform_update(self, serializer):
        department = serializer.save()
        write_audit(self.request.user, "update", "Department", department.id, f"Updated department {department.name}.", request=self.request)

    def destroy(self, request, *args, **kwargs):
        department = self.get_object()
        department.soft_delete()
        write_audit(request.user, "delete", "Department", department.id, f"Archived department {department.name}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademicSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicSessionSerializer
    permission_classes = [IsAdministrator]
    search_fields = ["name"]
    filterset_fields = ["is_current"]

    def get_queryset(self):
        return AcademicSession.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        session = serializer.save()
        if session.is_current:
            AcademicSession.objects.exclude(pk=session.pk).update(is_current=False)
        write_audit(self.request.user, "create", "AcademicSession", session.id, f"Created session {session.name}.", request=self.request)

    def perform_update(self, serializer):
        session = serializer.save()
        if session.is_current:
            AcademicSession.objects.exclude(pk=session.pk).update(is_current=False)
        write_audit(self.request.user, "update", "AcademicSession", session.id, f"Updated session {session.name}.", request=self.request)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.soft_delete()
        write_audit(request.user, "delete", "AcademicSession", session.id, f"Archived session {session.name}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SemesterViewSet(viewsets.ModelViewSet):
    serializer_class = SemesterSerializer
    permission_classes = [IsAdministrator]
    filterset_fields = ["session", "name", "is_current"]

    def get_queryset(self):
        return Semester.objects.filter(is_deleted=False).select_related("session")

    def perform_create(self, serializer):
        semester = serializer.save()
        if semester.is_current:
            Semester.objects.exclude(pk=semester.pk).update(is_current=False)
        write_audit(self.request.user, "create", "Semester", semester.id, f"Created {semester}.", request=self.request)

    def perform_update(self, serializer):
        semester = serializer.save()
        if semester.is_current:
            Semester.objects.exclude(pk=semester.pk).update(is_current=False)
        write_audit(self.request.user, "update", "Semester", semester.id, f"Updated {semester}.", request=self.request)


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    search_fields = ["matric_number", "first_name", "surname", "email", "programme"]
    filterset_fields = ["faculty", "department", "level", "status", "admission_year", "current_session", "gender"]
    ordering_fields = ["surname", "matric_number", "level", "current_cgpa"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Student.objects.none()
        return scoped_students(self.request.user)

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAdminOrLecturer()]
        if self.action == "me":
            from rest_framework.permissions import IsAuthenticated

            return [IsAuthenticated()]
        return [IsAdministrator()]

    @action(detail=False, methods=["get"])
    def me(self, request):
        student = getattr(request.user, "student_profile", None)
        if student is None or student.is_deleted:
            return Response({"detail": "No student profile is linked to this account."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(student).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.pop("password", None) or _temporary_password()
        generated = "password" not in request.data
        try:
            with transaction.atomic():
                student = serializer.save()
                user = User.objects.create_user(
                    email=student.email,
                    username=student.matric_number.replace("/", "-"),
                    password=password,
                    first_name=student.first_name,
                    last_name=student.surname,
                    role=User.Role.STUDENT,
                    phone=student.telephone,
                    is_active=student.status == Student.Status.ACTIVE,
                    is_sample=student.is_sample,
                )
                student.user = user
                student.save(update_fields=["user"])
        except IntegrityError:
            raise ValidationError("A student with this matriculation number or email already exists.")
        write_audit(request.user, "create", "Student", student.id, f"Registered student {student.matric_number}.", request=request)
        data = self.get_serializer(student).data
        if generated:
            data["temporary_password"] = password
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        password = serializer.validated_data.pop("password", None)
        student = serializer.save()
        if student.user:
            student.user.email = student.email
            student.user.username = student.matric_number.replace("/", "-")
            student.user.first_name = student.first_name
            student.user.last_name = student.surname
            student.user.phone = student.telephone
            student.user.is_active = student.status == Student.Status.ACTIVE
            if password:
                student.user.set_password(password)
            student.user.save()
        write_audit(self.request.user, "update", "Student", student.id, f"Updated student {student.matric_number}.", request=self.request)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        student = self.get_object()
        student.status = Student.Status.ACTIVE
        student.save(update_fields=["status", "updated_at"])
        if student.user:
            student.user.is_active = True
            student.user.save(update_fields=["is_active"])
        write_audit(request.user, "activate", "Student", student.id, f"Activated {student.matric_number}.", request=request)
        return Response(self.get_serializer(student).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        student = self.get_object()
        student.status = Student.Status.SUSPENDED
        student.save(update_fields=["status", "updated_at"])
        if student.user:
            student.user.is_active = False
            student.user.save(update_fields=["is_active"])
        write_audit(request.user, "deactivate", "Student", student.id, f"Deactivated {student.matric_number}.", request=request)
        return Response(self.get_serializer(student).data)

    def destroy(self, request, *args, **kwargs):
        student = self.get_object()
        student.soft_delete()
        if student.user:
            student.user.is_active = False
            student.user.save(update_fields=["is_active"])
        write_audit(request.user, "delete", "Student", student.id, f"Archived {student.matric_number}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LecturerViewSet(viewsets.ModelViewSet):
    serializer_class = LecturerSerializer
    permission_classes = [IsAdministrator]
    search_fields = ["staff_id", "first_name", "surname", "email"]
    filterset_fields = ["faculty", "department", "employment_status"]

    def get_queryset(self):
        return Lecturer.objects.filter(is_deleted=False).select_related("faculty", "department")

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAdminOrLecturer()]
        return [IsAdministrator()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.pop("password", None) or _temporary_password()
        generated = "password" not in request.data
        try:
            with transaction.atomic():
                lecturer = serializer.save()
                user = User.objects.create_user(
                    email=lecturer.email,
                    username=lecturer.staff_id,
                    password=password,
                    first_name=lecturer.first_name,
                    last_name=lecturer.surname,
                    role=User.Role.LECTURER,
                    phone=lecturer.telephone,
                    is_active=lecturer.employment_status == Lecturer.EmploymentStatus.ACTIVE,
                    is_sample=lecturer.is_sample,
                )
                lecturer.user = user
                lecturer.save(update_fields=["user"])
        except IntegrityError:
            raise ValidationError("A lecturer with this staff ID or email already exists.")
        write_audit(request.user, "create", "Lecturer", lecturer.id, f"Registered lecturer {lecturer.staff_id}.", request=request)
        data = self.get_serializer(lecturer).data
        if generated:
            data["temporary_password"] = password
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        password = serializer.validated_data.pop("password", None)
        lecturer = serializer.save()
        if lecturer.user:
            lecturer.user.email = lecturer.email
            lecturer.user.username = lecturer.staff_id
            lecturer.user.first_name = lecturer.first_name
            lecturer.user.last_name = lecturer.surname
            lecturer.user.phone = lecturer.telephone
            lecturer.user.is_active = lecturer.employment_status == Lecturer.EmploymentStatus.ACTIVE
            if password:
                lecturer.user.set_password(password)
            lecturer.user.save()
        write_audit(self.request.user, "update", "Lecturer", lecturer.id, f"Updated lecturer {lecturer.staff_id}.", request=self.request)

    @action(detail=True, methods=["post"])
    def assign_courses(self, request, pk=None):
        lecturer = self.get_object()
        course_ids = request.data.get("course_ids") or []
        primary_id = request.data.get("primary_course")
        if not isinstance(course_ids, list) or not course_ids:
            raise ValidationError({"course_ids": "Provide one or more courses."})
        courses = list(Course.objects.filter(id__in=course_ids, is_deleted=False))
        if len(courses) != len(set(course_ids)):
            raise ValidationError({"course_ids": "One or more courses could not be found."})
        for course in courses:
            CourseAssignment.objects.update_or_create(
                course=course,
                lecturer=lecturer,
                defaults={"is_primary": str(course.id) == str(primary_id), "is_sample": lecturer.is_sample},
            )
        write_audit(
            request.user,
            "assign",
            "Lecturer",
            lecturer.id,
            f"Assigned {len(courses)} course(s) to {lecturer.staff_id}.",
            request=request,
        )
        return Response(self.get_serializer(lecturer).data)


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    search_fields = ["code", "title"]
    filterset_fields = ["faculty", "department", "level", "academic_session", "semester", "status"]

    def get_queryset(self):
        query = Course.objects.filter(is_deleted=False).select_related("faculty", "department", "academic_session", "semester")
        user = self.request.user
        if not getattr(user, "is_authenticated", False):
            return query.none()
        if user.role == "lecturer":
            return query.filter(assignments__lecturer__user=user).distinct()
        if user.role == "student":
            student = getattr(user, "student_profile", None)
            if student is None:
                return query.none()
            return query.filter(enrolments__student=student, enrolments__is_deleted=False).distinct()
        return query

    def get_permissions(self):
        if self.action in {"list", "retrieve", "assigned"}:
            from rest_framework.permissions import IsAuthenticated

            return [IsAuthenticated()]
        return [IsAdministrator()]

    def perform_create(self, serializer):
        try:
            course = serializer.save()
        except IntegrityError:
            raise ValidationError("A course with this code already exists for the selected session and semester.")
        write_audit(self.request.user, "create", "Course", course.id, f"Created course {course.code}.", request=self.request)

    def perform_update(self, serializer):
        try:
            course = serializer.save()
        except IntegrityError:
            raise ValidationError("A course with this code already exists for the selected session and semester.")
        write_audit(self.request.user, "update", "Course", course.id, f"Updated course {course.code}.", request=self.request)

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        course.soft_delete()
        course.status = Course.Status.INACTIVE
        course.save(update_fields=["status", "updated_at"])
        write_audit(request.user, "delete", "Course", course.id, f"Archived course {course.code}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def assigned(self, request):
        if request.user.role != "lecturer":
            raise PermissionDenied("Only lecturers can view assigned courses from this endpoint.")
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        course = self.get_object()
        lecturer = Lecturer.objects.filter(pk=request.data.get("lecturer"), is_deleted=False).first()
        if lecturer is None:
            raise ValidationError({"lecturer": "Select a valid lecturer."})
        assignment, _created = CourseAssignment.objects.update_or_create(
            course=course,
            lecturer=lecturer,
            defaults={"is_primary": bool(request.data.get("is_primary", True))},
        )
        if assignment.is_primary:
            course.assignments.exclude(pk=assignment.pk).update(is_primary=False)
        write_audit(request.user, "assign", "Course", course.id, f"Assigned {lecturer.staff_id} to {course.code}.", request=request)
        return Response(CourseAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class EnrolmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrolmentSerializer
    permission_classes = [IsAdminOrLecturer]
    filterset_fields = ["session", "semester", "course", "student", "status"]
    search_fields = ["student__matric_number", "student__surname", "course__code"]

    def get_queryset(self):
        query = scoped_enrolments(self.request.user)
        level = self.request.query_params.get("level")
        department = self.request.query_params.get("department")
        faculty = self.request.query_params.get("faculty")
        if level:
            query = query.filter(student__level=level)
        if department:
            query = query.filter(student__department_id=department)
        if faculty:
            query = query.filter(student__faculty_id=faculty)
        return query

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated

        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsAdminOrLecturer()]

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if self.request.user.role == "lecturer":
            from apps.records.services import lecturer_can_access_course

            if not lecturer_can_access_course(self.request.user, course.id):
                raise PermissionDenied("You can only enrol students in courses assigned to you.")
        try:
            enrolment = serializer.save()
        except IntegrityError:
            raise ValidationError("This student is already enrolled in the course.")
        write_audit(
            self.request.user,
            "enrol",
            "Enrolment",
            enrolment.id,
            f"Enrolled {enrolment.student.matric_number} in {enrolment.course.code}.",
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        enrolment = self.get_object()
        enrolment.soft_delete()
        enrolment.status = Enrolment.Status.DROPPED
        enrolment.save(update_fields=["status", "updated_at"])
        write_audit(request.user, "drop", "Enrolment", enrolment.id, f"Dropped enrolment {enrolment.id}.", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "Upload a CSV file with matric_number and course_code columns."})
        try:
            content = upload.read().decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(content)))
        except UnicodeDecodeError:
            raise ValidationError({"file": "The file must be a UTF-8 CSV."})
        created = 0
        errors = []
        for index, row in enumerate(rows, start=2):
            matric = (row.get("matric_number") or "").strip()
            code = (row.get("course_code") or "").strip()
            session_name = (row.get("session") or "").strip()
            semester_name = (row.get("semester") or "").strip()
            student = Student.objects.filter(matric_number__iexact=matric, is_deleted=False).first()
            courses = Course.objects.filter(code__iexact=code, is_deleted=False)
            if session_name:
                courses = courses.filter(academic_session__name=session_name)
            if semester_name:
                courses = courses.filter(semester__name=semester_name.lower())
            course = courses.first()
            if student is None or course is None:
                errors.append({"row": index, "detail": "Student or course was not found."})
                continue
            if request.user.role == "lecturer":
                from apps.records.services import lecturer_can_access_course

                if not lecturer_can_access_course(request.user, course.id):
                    errors.append({"row": index, "detail": "You are not assigned to this course."})
                    continue
            if Enrolment.objects.filter(student=student, course=course, is_deleted=False).exists():
                errors.append({"row": index, "detail": "Duplicate enrolment skipped."})
                continue
            Enrolment.objects.create(student=student, course=course, session=course.academic_session, semester=course.semester)
            created += 1
        write_audit(request.user, "import", "Enrolment", "", f"Imported {created} enrolment records.", request=request)
        return Response({"created": created, "errors": errors})
