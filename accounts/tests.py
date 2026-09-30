from django.contrib.auth import get_user_model
from django.urls import reverse
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

    def test_rotated_refresh_token_is_returned_and_usable(self):
        first = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        rotated = first.data["refresh"]

        self.assertNotEqual(rotated, self.refresh)
        again = self.client.post(self.url, {"refresh": rotated}, format="json")
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
    """
    Email must be unique: otherwise anyone could register on someone
    else's address and reach their account.
    """

    def register(self, username, email):
        return self.client.post(
            reverse("auth-register"),
            {
                "username": username,
                "email": email,
                "password": "Str0ngPass!123",
                "password2": "Str0ngPass!123",
            },
            format="json",
        )

    def test_duplicate_email_is_rejected_with_400(self):
        first = self.register("owner", "owner@example.com")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.register("intruder", "owner@example.com")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", second.data)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.register("owner2", "Owner2@Example.com")
        again = self.register("intruder2", "owner2@example.com")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_email_is_allowed_for_many_users(self):
        a = self.register("noemail1", "")
        b = self.register("noemail2", "")
        self.assertEqual(a.status_code, status.HTTP_201_CREATED)
        self.assertEqual(b.status_code, status.HTTP_201_CREATED)

    def test_email_is_stored_normalised(self):
        self.register("norm", "  MiXeD@Example.COM ")
        user = User.objects.get(username="norm")
        self.assertEqual(user.email, "mixed@example.com")


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
