from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import ensure_default_settings
from apps.academics.models import AcademicSession, Course, Department, Enrolment, Faculty, Lecturer, Semester, Student


def client_for(user):
    api = APIClient()
    response = api.post("/api/v1/auth/login/", {"identifier": user.email, "password": "Sample@12345"}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api, response


def make_user(email, role, password="Sample@12345", **extra):
    return User.objects.create_user(
        email=email,
        username=extra.pop("username", email),
        password=password,
        first_name=extra.pop("first_name", "Test"),
        last_name=extra.pop("last_name", "User"),
        role=role,
        is_active=extra.pop("is_active", True),
        **extra,
    )


def make_structure():
    ensure_default_settings()
    faculty = Faculty.objects.create(name="Faculty of Science", code="SCI")
    department = Department.objects.create(faculty=faculty, name="Computer Science", code="CSC")
    session = AcademicSession.objects.create(name="2026/2027", start_date="2026-09-14", end_date="2027-07-30", is_current=True)
    semester = Semester.objects.create(session=session, name=Semester.Name.FIRST, is_current=True)
    return faculty, department, session, semester


def make_student(department, session, matric="NSU/2026/001", email="student@example.com"):
    user = make_user(email, User.Role.STUDENT, username=matric.replace("/", "-"), first_name="Ada", last_name="Okonkwo")
    return Student.objects.create(
        user=user,
        matric_number=matric,
        first_name="Ada",
        surname="Okonkwo",
        email=email,
        telephone="08031234567",
        gender=Student.Gender.FEMALE,
        date_of_birth="2006-04-12",
        faculty=department.faculty,
        department=department,
        programme="B.Sc. Computer Science",
        level=100,
        admission_year=2026,
        current_session=session,
        prior_cgpa=3.2,
    )


def make_lecturer(department, email="lecturer@example.com", staff_id="STAFF001"):
    user = make_user(email, User.Role.LECTURER, username=staff_id, first_name="Chinedu", last_name="Bello")
    return Lecturer.objects.create(
        user=user,
        staff_id=staff_id,
        first_name="Chinedu",
        surname="Bello",
        email=email,
        faculty=department.faculty,
        department=department,
    )


def make_course(department, session, semester, code="CSC101", lecturer=None):
    course = Course.objects.create(
        code=code,
        title="Introduction to Computing",
        credit_units=3,
        faculty=department.faculty,
        department=department,
        level=100,
        academic_session=session,
        semester=semester,
    )
    if lecturer:
        course.assignments.create(lecturer=lecturer, is_primary=True)
    return course


def enrol(student, course):
    return Enrolment.objects.create(student=student, course=course, session=course.academic_session, semester=course.semester)
