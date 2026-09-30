from rest_framework import serializers

from apps.records.models import Assessment, Attendance, Result
from apps.records.services import attendance_stats


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrolment.student.full_name", read_only=True)
    matric_number = serializers.CharField(source="enrolment.student.matric_number", read_only=True)
    course_code = serializers.CharField(source="enrolment.course.code", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "enrolment",
            "student_name",
            "matric_number",
            "course_code",
            "date",
            "status",
            "marked_by",
            "is_sample",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["marked_by", "is_sample", "created_at", "updated_at"]


class AssessmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="enrolment.student.full_name", read_only=True)
    matric_number = serializers.CharField(source="enrolment.student.matric_number", read_only=True)
    course_code = serializers.CharField(source="enrolment.course.code", read_only=True)
    grade = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id",
            "enrolment",
            "student_name",
            "matric_number",
            "course_code",
            "ca_score",
            "exam_score",
            "grade",
            "total_score",
            "recorded_by",
            "is_sample",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["recorded_by", "is_sample", "created_at", "updated_at"]

    def _linked_result(self, obj):
        try:
            return obj.result
        except Result.DoesNotExist:
            return None

    def get_grade(self, obj):
        result = self._linked_result(obj)
        return result.grade if result else None

    def get_total_score(self, obj):
        result = self._linked_result(obj)
        return result.total_score if result else None


class ResultSerializer(serializers.ModelSerializer):
    student = serializers.IntegerField(source="enrolment.student_id", read_only=True)
    student_name = serializers.CharField(source="enrolment.student.full_name", read_only=True)
    matric_number = serializers.CharField(source="enrolment.student.matric_number", read_only=True)
    course = serializers.IntegerField(source="enrolment.course_id", read_only=True)
    course_code = serializers.CharField(source="enrolment.course.code", read_only=True)
    course_title = serializers.CharField(source="enrolment.course.title", read_only=True)
    credit_units = serializers.IntegerField(source="enrolment.course.credit_units", read_only=True)
    session_name = serializers.CharField(source="enrolment.session.name", read_only=True)
    semester_name = serializers.CharField(source="enrolment.semester.get_name_display", read_only=True)
    ca_score = serializers.DecimalField(source="assessment.ca_score", max_digits=5, decimal_places=2, read_only=True)
    exam_score = serializers.DecimalField(source="assessment.exam_score", max_digits=5, decimal_places=2, read_only=True)
    faculty = serializers.CharField(source="enrolment.student.faculty.name", read_only=True)
    department = serializers.CharField(source="enrolment.student.department.name", read_only=True)
    level = serializers.IntegerField(source="enrolment.student.level", read_only=True)
    attendance_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Result
        fields = [
            "id",
            "enrolment",
            "student",
            "student_name",
            "matric_number",
            "course",
            "course_code",
            "course_title",
            "credit_units",
            "session_name",
            "semester_name",
            "faculty",
            "department",
            "level",
            "ca_score",
            "exam_score",
            "total_score",
            "grade",
            "grade_point",
            "remark",
            "attendance_percentage",
            "is_validated",
            "is_locked",
            "is_sample",
            "created_at",
        ]
        read_only_fields = [
            "total_score",
            "grade",
            "grade_point",
            "remark",
            "is_validated",
            "is_sample",
            "created_at",
        ]

    def get_attendance_percentage(self, obj):
        return attendance_stats(obj.enrolment)["percentage"]
