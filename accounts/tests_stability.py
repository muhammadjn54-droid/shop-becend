from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

User = get_user_model()


class SessionStabilityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.password = "  Strong-Pass123!  "
        self.user = User.objects.create_user(username="stable-user", email="stable@example.com", password=self.password)

    def login(self):
        response = self.client.post("/api/auth/login/", {"username": self.user.username, "password": self.password})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_login_and_registration_ignore_expired_authorization(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        self.assertEqual(self.login()["user"]["id"], self.user.id)
        response = self.client.post("/api/auth/register/", {
            "username": "new-registration", "password": self.password, "password2": self.password,
        })
        self.assertEqual(response.status_code, 201, response.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_profile_rename_keeps_token_valid_and_new_login_works(self):
        tokens = self.login()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        response = self.client.patch("/api/auth/me/", {"username": "new-name", "first_name": "Ali", "last_name": "Test", "email": "other@example.com", "is_superuser": True})
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new-name")
        self.assertEqual(self.user.email, "stable@example.com")
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.client.get("/api/auth/me/").data["first_name"], "Ali")
        self.assertEqual(self.login()["user"]["username"], "new-name")

    def test_duplicate_and_cross_namespace_profile_names_are_rejected(self):
        User.objects.create_user(username="other-user", email="other@example.com", password="Str0ngPass!123")
        self.client.force_authenticate(self.user)
        for username in ("OTHER-USER", "OTHER@example.com"):
            response = self.client.patch("/api/auth/me/", {"username": username})
            self.assertEqual(response.status_code, 400, response.data)

    def test_logout_with_expired_access_revokes_refresh(self):
        tokens = self.login()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code, 401)

    def test_password_reset_revokes_existing_access_and_refresh(self):
        tokens = self.login()
        self.user.refresh_from_db()
        token = default_token_generator.make_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        response = self.client.post("/api/auth/reset-password/", {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)), "token": token,
            "password": "New-StrongPassword456!", "confirm_password": "New-StrongPassword456!",
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code, 401)

    def test_disabled_user_cannot_refresh(self):
        tokens = self.login()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code, 401)

    def test_fresh_migrations_do_not_create_a_default_admin(self):
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
