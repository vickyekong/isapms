from datetime import date

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

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


def _faculty_department_match(faculty, department):
    if faculty and department and department.faculty_id != faculty.id:
        raise serializers.ValidationError({"department": "Select a department that belongs to the chosen faculty."})


class FacultySerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = ["id", "name", "code", "description", "is_active", "is_sample", "department_count", "created_at"]
        read_only_fields = ["is_sample", "created_at"]

    def get_department_count(self, obj):
        return obj.departments.filter(is_deleted=False).count()


class DepartmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "faculty", "faculty_name", "name", "code", "is_active", "is_sample", "created_at"]
        read_only_fields = ["is_sample", "created_at"]


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ["id", "name", "start_date", "end_date", "is_current", "is_sample", "created_at"]
        read_only_fields = ["is_sample", "created_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "The session must end after it starts."})
        return attrs


class SemesterSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    label = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Semester
        fields = ["id", "session", "session_name", "name", "label", "is_current", "is_sample", "created_at"]
        read_only_fields = ["is_sample", "created_at"]


class StudentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    session_name = serializers.CharField(source="current_session.name", read_only=True)
    full_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Student
        fields = [
            "id",
            "user",
            "matric_number",
            "first_name",
            "surname",
            "full_name",
            "email",
            "telephone",
            "gender",
            "date_of_birth",
            "faculty",
            "faculty_name",
            "department",
            "department_name",
            "programme",
            "level",
            "admission_year",
            "current_session",
            "session_name",
            "prior_cgpa",
            "current_cgpa",
            "status",
            "is_sample",
            "password",
            "created_at",
        ]
        read_only_fields = ["user", "current_cgpa", "is_sample", "created_at"]

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate_date_of_birth(self, value):
        if value >= date.today():
            raise serializers.ValidationError("Date of birth must be in the past.")
        if value.year < 1950:
            raise serializers.ValidationError("Enter a valid date of birth.")
        return value

    def validate_telephone(self, value):
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) < 7 or len(digits) > 15:
            raise serializers.ValidationError("Enter a valid telephone number.")
        return value

    def validate(self, attrs):
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        _faculty_department_match(faculty, department)
        return attrs


class LecturerSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    full_name = serializers.CharField(read_only=True)
    assigned_courses = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Lecturer
        fields = [
            "id",
            "user",
            "staff_id",
            "first_name",
            "surname",
            "full_name",
            "email",
            "telephone",
            "faculty",
            "faculty_name",
            "department",
            "department_name",
            "employment_status",
            "assigned_courses",
            "is_sample",
            "password",
            "created_at",
        ]
        read_only_fields = ["user", "is_sample", "created_at"]

    def get_assigned_courses(self, obj):
        return [
            {"id": assignment.course_id, "code": assignment.course.code, "title": assignment.course.title, "is_primary": assignment.is_primary}
            for assignment in obj.assignments.select_related("course")
        ]

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate(self, attrs):
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        _faculty_department_match(faculty, department)
        return attrs


class CourseSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    session_name = serializers.CharField(source="academic_session.name", read_only=True)
    semester_name = serializers.CharField(source="semester.get_name_display", read_only=True)
    lecturers = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "credit_units",
            "faculty",
            "faculty_name",
            "department",
            "department_name",
            "level",
            "academic_session",
            "session_name",
            "semester",
            "semester_name",
            "status",
            "lecturers",
            "is_sample",
            "created_at",
        ]
        read_only_fields = ["is_sample", "created_at"]

    def get_lecturers(self, obj):
        return [
            {"id": assignment.lecturer_id, "staff_id": assignment.lecturer.staff_id, "name": assignment.lecturer.full_name, "is_primary": assignment.is_primary}
            for assignment in obj.assignments.select_related("lecturer")
        ]

    def validate(self, attrs):
        faculty = attrs.get("faculty", getattr(self.instance, "faculty", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        session = attrs.get("academic_session", getattr(self.instance, "academic_session", None))
        semester = attrs.get("semester", getattr(self.instance, "semester", None))
        _faculty_department_match(faculty, department)
        if session and semester and semester.session_id != session.id:
            raise serializers.ValidationError({"semester": "The semester must belong to the selected academic session."})
        return attrs


class CourseAssignmentSerializer(serializers.ModelSerializer):
    lecturer_name = serializers.CharField(source="lecturer.full_name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)

    class Meta:
        model = CourseAssignment
        fields = ["id", "course", "course_code", "lecturer", "lecturer_name", "is_primary", "assigned_at", "is_sample"]
        read_only_fields = ["assigned_at", "is_sample"]


class EnrolmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    matric_number = serializers.CharField(source="student.matric_number", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    semester_name = serializers.CharField(source="semester.get_name_display", read_only=True)

    class Meta:
        model = Enrolment
        fields = [
            "id",
            "student",
            "student_name",
            "matric_number",
            "course",
            "course_code",
            "course_title",
            "session",
            "session_name",
            "semester",
            "semester_name",
            "status",
            "is_sample",
            "created_at",
        ]
        read_only_fields = ["session", "semester", "is_sample", "created_at"]

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        course = attrs.get("course", getattr(self.instance, "course", None))
        if student and course and Enrolment.objects.filter(student=student, course=course, is_deleted=False).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError("This student is already enrolled in the course.")
        return attrs

    def create(self, validated_data):
        course = validated_data["course"]
        validated_data["session"] = course.academic_session
        validated_data["semester"] = course.semester
        return super().create(validated_data)
