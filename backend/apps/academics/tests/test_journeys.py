from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.records.services import apply_assessment
from apps.testing import client_for, enrol, make_course, make_lecturer, make_structure, make_student, make_user


class AcademicJourneyTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com", User.Role.ADMIN, first_name="Amina", last_name="Bello")
        self.faculty, self.department, self.session, self.semester = make_structure()
        self.client, _response = client_for(self.admin)

    def test_registration_course_enrolment_attendance_and_grading(self):
        lecturer = self.client.post(
            "/api/v1/lecturers/",
            {
                "staff_id": "NSU-STAFF-001",
                "first_name": "Chinedu",
                "surname": "Bello",
                "email": "lecturer@example.com",
                "telephone": "08031234567",
                "faculty": self.faculty.id,
                "department": self.department.id,
                "password": "Sample@12345",
            },
            format="json",
        )
        self.assertEqual(lecturer.status_code, 201, lecturer.data)
        course = self.client.post(
            "/api/v1/courses/",
            {
                "code": "CSC101",
                "title": "Introduction to Computing",
                "credit_units": 3,
                "faculty": self.faculty.id,
                "department": self.department.id,
                "level": 100,
                "academic_session": self.session.id,
                "semester": self.semester.id,
            },
            format="json",
        )
        self.assertEqual(course.status_code, 201, course.data)
        duplicate = self.client.post(
            "/api/v1/courses/",
            {
                "code": "CSC101",
                "title": "Duplicate",
                "credit_units": 2,
                "faculty": self.faculty.id,
                "department": self.department.id,
                "level": 100,
                "academic_session": self.session.id,
                "semester": self.semester.id,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)
        assigned = self.client.post(
            f"/api/v1/courses/{course.data['id']}/assign/",
            {"lecturer": lecturer.data["id"], "is_primary": True},
            format="json",
        )
        self.assertEqual(assigned.status_code, 201, assigned.data)
        student = self.client.post(
            "/api/v1/students/",
            {
                "matric_number": "NSU/2026/014",
                "first_name": "Fatima",
                "surname": "Danjuma",
                "email": "fatima@example.com",
                "telephone": "08037654321",
                "gender": "female",
                "date_of_birth": "2005-08-19",
                "faculty": self.faculty.id,
                "department": self.department.id,
                "programme": "B.Sc. Computer Science",
                "level": 100,
                "admission_year": 2026,
                "current_session": self.session.id,
                "prior_cgpa": "3.40",
                "password": "Sample@12345",
            },
            format="json",
        )
        self.assertEqual(student.status_code, 201, student.data)
        enrolment = self.client.post(
            "/api/v1/enrolments/",
            {"student": student.data["id"], "course": course.data["id"]},
            format="json",
        )
        self.assertEqual(enrolment.status_code, 201, enrolment.data)
        duplicate_enrolment = self.client.post(
            "/api/v1/enrolments/",
            {"student": student.data["id"], "course": course.data["id"]},
            format="json",
        )
        self.assertEqual(duplicate_enrolment.status_code, 400)
        marked = self.client.post(
            "/api/v1/attendance/mark/",
            {
                "course": course.data["id"],
                "date": "2026-09-20",
                "records": [{"enrolment": enrolment.data["id"], "status": "present"}],
            },
            format="json",
        )
        self.assertEqual(marked.status_code, 200, marked.data)
        uploaded = self.client.post(
            "/api/v1/assessments/upload/",
            {"course": course.data["id"], "scores": [{"enrolment": enrolment.data["id"], "ca_score": 30, "exam_score": 40}]},
            format="json",
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.data)
        self.assertEqual(uploaded.data[0]["grade"], "A")
        self.assertEqual(float(uploaded.data[0]["total_score"]), 70)
        rejected = self.client.post(
            "/api/v1/assessments/upload/",
            {"course": course.data["id"], "scores": [{"enrolment": enrolment.data["id"], "ca_score": 50, "exam_score": 10}]},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        dashboard = self.client.get("/api/v1/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["totals"]["students"], 1)
        report = self.client.get("/api/v1/reports/?type=results&format=csv")
        self.assertEqual(report.status_code, 200)
        self.assertIn(b"Fatima", report.content)

    def test_lecturer_cannot_score_unassigned_course(self):
        lecturer = make_lecturer(self.department)
        other = make_course(self.department, self.session, self.semester, code="MTH101")
        student = make_student(self.department, self.session)
        enrolment = enrol(student, other)
        lecturer_client, _response = client_for(lecturer.user)
        response = lecturer_client.post(
            "/api/v1/assessments/upload/",
            {"course": other.id, "scores": [{"enrolment": enrolment.id, "ca_score": 20, "exam_score": 30}]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_duplicate_matric_is_rejected(self):
        payload = {
            "matric_number": "NSU/2026/001",
            "first_name": "Ada",
            "surname": "Okonkwo",
            "email": "ada1@example.com",
            "telephone": "08030000001",
            "gender": "female",
            "date_of_birth": "2006-01-01",
            "faculty": self.faculty.id,
            "department": self.department.id,
            "programme": "B.Sc. Computer Science",
            "level": 100,
            "admission_year": 2026,
            "prior_cgpa": "0",
            "password": "Sample@12345",
        }
        first = self.client.post("/api/v1/students/", payload, format="json")
        payload["email"] = "ada2@example.com"
        second = self.client.post("/api/v1/students/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400)

    def test_model_constraint_blocks_duplicate_enrolment_rows(self):
        student = make_student(self.department, self.session)
        course = make_course(self.department, self.session, self.semester)
        enrol(student, course)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                enrol(student, course)
        apply_assessment(
            student.enrolments.get(),
            32,
            48,
            self.admin,
        )
        student.refresh_from_db()
        self.assertEqual(float(student.current_cgpa), 5)
