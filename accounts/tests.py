from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthTests(APITestCase):
    def test_register_returns_tokens(self):
        url = reverse("auth-register")
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Str0ngPass!123",
            "password2": "Str0ngPass!123",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "newuser")

    def test_register_password_mismatch(self):
        url = reverse("auth-register")
        data = {
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "Str0ngPass!123",
            "password2": "WrongPass!456",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        User.objects.create_user(username="existing", password="Str0ngPass!123")
        url = reverse("auth-register")
        data = {
            "username": "EXISTING",
            "email": "other@example.com",
            "password": "Str0ngPass!123",
            "password2": "Str0ngPass!123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_login_and_me(self):
        User.objects.create_user(username="loginuser", password="Str0ngPass!123")

        login_url = reverse("auth-login")
        response = self.client.post(
            login_url,
            {"username": "loginuser", "password": "Str0ngPass!123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_response = self.client.get(reverse("auth-me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], "loginuser")



class RefreshTokenRaceTests(APITestCase):
    """
    Two browser tabs share localStorage but not JS memory, so they can
    refresh with the same token at the same time. With
    BLACKLIST_AFTER_ROTATION enabled the loser of that race received 401,
    and the frontend 401 handler then wiped the shared tokens - logging
    the user out of every tab at once.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="racetab", password="Str0ngPass!123"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"username": "racetab", "password": "Str0ngPass!123"},
            format="json",
        )
        self.refresh = login.data["refresh"]
        self.url = reverse("auth-token-refresh")

    def test_same_refresh_token_can_be_used_twice(self):
        first = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        second = self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertIn("access", second.data)

    def test_refresh_token_remains_usable_without_rotation(self):
        first = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertNotIn("refresh", first.data)
        again = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(again.status_code, status.HTTP_200_OK)

    def test_logout_still_blacklists_the_token(self):
        # Disabling rotation blacklisting must not weaken explicit logout.
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.client.post(reverse('auth-login'), {'username': 'racetab', 'password': 'Str0ngPass!123'}, format='json').data['access']}"
        )
        out = self.client.post(
            reverse("auth-logout"), {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(out.status_code, status.HTTP_200_OK)

        after = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(after.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_lifetime_is_long_enough(self):
        from datetime import timedelta

        from django.conf import settings

        self.assertGreaterEqual(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta(days=7)
        )


class EmailUniquenessTests(APITestCase):
    def test_duplicate_email_raises_integrity_error(self):
        from django.db import IntegrityError
        User.objects.create_user("owner", "owner@example.com", "Str0ngPass!123")
        with self.assertRaises(IntegrityError):
            User.objects.create_user("intruder", "owner@example.com", "Str0ngPass!123")

    def test_empty_email_is_allowed_for_many_users(self):
        u1 = User.objects.create_user("noemail1", None, "Str0ngPass!123")
        u2 = User.objects.create_user("noemail2", None, "Str0ngPass!123")
        self.assertIsNotNone(u1.pk)
        self.assertIsNotNone(u2.pk)

    def test_email_is_stored_normalised(self):
        u = User.objects.create_user("norm", "  MiXeD@Example.COM ", "Str0ngPass!123")
        self.assertEqual(u.email, "MiXeD@example.com")


class LoginWithEmailTests(APITestCase):
    def setUp(self):
        User.objects.create_user(
            username="shopowner",
            email="shopowner@example.com",
            password="Str0ngPass!123",
        )

    def test_login_with_email(self):
        response = self.client.post(
            reverse("auth-login"),
            {"username": "shopowner@example.com", "password": "Str0ngPass!123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_username_still_works(self):
        response = self.client.post(
            reverse("auth-login"),
            {"username": "shopowner", "password": "Str0ngPass!123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_wrong_password_gives_same_error_as_unknown_user(self):
        wrong_pw = self.client.post(
            reverse("auth-login"),
            {"username": "shopowner", "password": "WrongPass!123"},
            format="json",
        )
        unknown = self.client.post(
            reverse("auth-login"),
            {"username": "ghost", "password": "WrongPass!123"},
            format="json",
        )
        self.assertEqual(wrong_pw.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_pw.data["detail"], unknown.data["detail"])


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="resetuser",
            email="resetuser@example.com",
            password="OldPassword123!",
        )

    def test_password_reset_request_sends_email(self):
        url = reverse("auth-forgot-password")
        response = self.client.post(url, {"email": "resetuser@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "If an account with this email exists, a password reset link has been sent.",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Reset your password")
        self.assertIn("Click the link below to create a new password:", mail.outbox[0].body)
        self.assertIn("reset-password?uid=", mail.outbox[0].body)

    def test_password_reset_request_unknown_email_does_not_reveal_existence(self):
        url = reverse("auth-forgot-password")
        response = self.client.post(url, {"email": "nonexistent@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"],
            "If an account with this email exists, a password reset link has been sent.",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_successful_and_invalidates_old_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        url = reverse("auth-reset-password")
        response = self.client.post(
            url,
            {
                "uid": uid,
                "token": token,
                "password": "NewSecretPassword123!",
                "confirm_password": "NewSecretPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Password reset successfully.")

        # Old password must no longer work
        old_login = self.client.post(
            reverse("auth-login"),
            {"username": "resetuser", "password": "OldPassword123!"},
            format="json",
        )
        self.assertEqual(old_login.status_code, status.HTTP_400_BAD_REQUEST)

        # Login with new password must succeed
        new_login = self.client.post(
            reverse("auth-login"),
            {"username": "resetuser", "password": "NewSecretPassword123!"},
            format="json",
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

        # Token cannot be reused
        reuse = self.client.post(
            url,
            {
                "uid": uid,
                "token": token,
                "password": "AnotherPassword123!",
                "confirm_password": "AnotherPassword123!",
            },
            format="json",
        )
        self.assertEqual(reuse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse("auth-reset-password")
        response = self.client.post(
            url,
            {
                "uid": uid,
                "token": "invalid-token-12345",
                "password": "NewSecretPassword123!",
                "confirm_password": "NewSecretPassword123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
