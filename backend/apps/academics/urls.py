from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics.views import (
    AcademicSessionViewSet,
    CourseViewSet,
    EnrolmentViewSet,
    DepartmentViewSet,
    FacultyViewSet,
    LecturerViewSet,
    SemesterViewSet,
    StudentViewSet,
)
from apps.records.views import AssessmentViewSet, AttendanceViewSet, ResultViewSet

router = DefaultRouter()
router.register("faculties", FacultyViewSet, basename="faculty")
router.register("departments", DepartmentViewSet, basename="department")
router.register("sessions", AcademicSessionViewSet, basename="session")
router.register("semesters", SemesterViewSet, basename="semester")
router.register("students", StudentViewSet, basename="student")
router.register("lecturers", LecturerViewSet, basename="lecturer")
router.register("courses", CourseViewSet, basename="course")
router.register("enrolments", EnrolmentViewSet, basename="enrolment")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("assessments", AssessmentViewSet, basename="assessment")
router.register("results", ResultViewSet, basename="result")

urlpatterns = [path("", include(router.urls))]
