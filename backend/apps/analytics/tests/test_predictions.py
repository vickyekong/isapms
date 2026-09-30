from django.test import TestCase

from apps.accounts.models import User
from apps.analytics.engine import PREDICTION_DISCLAIMER, train_model
from apps.records.models import Attendance
from apps.records.services import apply_assessment
from apps.testing import client_for, enrol, make_course, make_structure, make_student, make_user


GRADE_SCORES = {
    "A": (32, 48),
    "B": (24, 40),
    "C": (18, 36),
    "D": (12, 35),
    "F": (8, 20),
}


class PredictionTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com", User.Role.ADMIN)
        self.faculty, self.department, self.session, self.semester = make_structure()
        self.client, _response = client_for(self.admin)
        self.course = make_course(self.department, self.session, self.semester)

    def _seed_training_results(self):
        index = 0
        for grade, (ca_score, exam_score) in GRADE_SCORES.items():
            for _copy in range(8):
                index += 1
                student = make_student(
                    self.department,
                    self.session,
                    matric=f"NSU/2026/{index:03d}",
                    email=f"learner{index}@example.com",
                )
                enrolment = enrol(student, self.course)
                Attendance.objects.create(enrolment=enrolment, date="2026-09-20", status="present")
                apply_assessment(enrolment, ca_score, exam_score, self.admin, sample=True)

    def test_prediction_requires_assessment_data(self):
        student = make_student(self.department, self.session)
        enrolment = enrol(student, self.course)
        response = self.client.post(
            "/api/v1/predictions/",
            {"student": student.id, "course": self.course.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("enough academic records", response.data["detail"])

    def test_student_cannot_run_predictions(self):
        student = make_student(self.department, self.session, matric="NSU/2026/900", email="own@example.com")
        student_client, _response = client_for(student.user)
        response = student_client.post(
            "/api/v1/predictions/",
            {"student": student.id, "course": self.course.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_training_prediction_risk_and_partial_forecast(self):
        self._seed_training_results()
        model_version = train_model(actor=self.admin, sample=True)
        self.assertGreaterEqual(model_version.training_rows, 1)
        self.assertIn("matrix", model_version.confusion_matrix)

        target = make_student(self.department, self.session, matric="NSU/2026/777", email="target@example.com")
        enrolment = enrol(target, self.course)
        Attendance.objects.create(enrolment=enrolment, date="2026-10-01", status="present")
        apply_assessment(enrolment, 30, None, self.admin)

        response = self.client.post(
            "/api/v1/predictions/",
            {"student": target.id, "course": self.course.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn(response.data["predicted_grade"], {"A", "B", "C", "D", "F"})
        self.assertEqual(response.data["data_status"], "partial")
        self.assertEqual(response.data["disclaimer"], PREDICTION_DISCLAIMER)
        self.assertIn(response.data["risk_level"], {"low", "medium", "high"})

        at_risk = self.client.get("/api/v1/predictions/at-risk/")
        self.assertEqual(at_risk.status_code, 200)
        self.assertIn("results", at_risk.data)
