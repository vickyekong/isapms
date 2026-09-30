from django.core import mail
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.testing import client_for, make_user


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com", User.Role.ADMIN, first_name="Amina", last_name="Bello")

    def test_administrator_login_and_refresh(self):
        api, response = client_for(self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "admin")
        refreshed = api.post("/api/v1/auth/refresh/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("access", refreshed.data)

    def test_login_rejects_bad_password_and_inactive_user(self):
        api = self.client
        bad = api.post("/api/v1/auth/login/", {"identifier": "admin@example.com", "password": "wrong-pass"}, format="json")
        self.assertEqual(bad.status_code, 401)
        self.admin.is_active = False
        self.admin.save()
        inactive = api.post("/api/v1/auth/login/", {"identifier": "admin@example.com", "password": "Sample@12345"}, format="json")
        self.assertEqual(inactive.status_code, 403)

    def test_password_reset_flow(self):
        response = self.client.post("/api/v1/auth/password-reset/", {"email": "admin@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        link = [line for line in mail.outbox[0].body.splitlines() if "uid=" in line][0]
        uid = link.split("uid=")[1].split("&")[0]
        token = link.split("token=")[1]
        confirm = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "password": "Newpass@123"},
            format="json",
        )
        self.assertEqual(confirm.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Newpass@123"))

    def test_logout_blacklists_refresh_token(self):
        api, response = client_for(self.admin)
        logout = api.post("/api/v1/auth/logout/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(logout.status_code, 200)
        reused = api.post("/api/v1/auth/refresh/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(reused.status_code, 401)
