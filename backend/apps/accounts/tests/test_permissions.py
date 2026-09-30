from django.test import TestCase

from apps.accounts.models import User
from apps.testing import client_for, make_structure, make_student, make_user


class PermissionTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com", User.Role.ADMIN)
        faculty, department, session, semester = make_structure()
        self.student = make_student(department, session)
        self.admin_client, _response = client_for(self.admin)
        self.student_client, _response = client_for(self.student.user)

    def test_student_cannot_manage_users_or_faculties(self):
        users = self.student_client.get("/api/v1/users/")
        faculties = self.student_client.post("/api/v1/faculties/", {"name": "Blocked", "code": "BLK"}, format="json")
        self.assertEqual(users.status_code, 403)
        self.assertEqual(faculties.status_code, 403)

    def test_student_can_view_only_own_profile(self):
        own = self.student_client.get("/api/v1/students/me/")
        listing = self.student_client.get("/api/v1/students/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data["matric_number"], self.student.matric_number)
        self.assertEqual(listing.status_code, 403)

    def test_admin_can_deactivate_another_user(self):
        response = self.admin_client.post(f"/api/v1/users/{self.student.user_id}/deactivate/")
        self.assertEqual(response.status_code, 200)
        self.student.user.refresh_from_db()
        self.assertFalse(self.student.user.is_active)
