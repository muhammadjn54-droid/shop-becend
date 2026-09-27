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
