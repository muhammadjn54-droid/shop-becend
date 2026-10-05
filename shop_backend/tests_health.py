from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch


class HealthEndpointTests(TestCase):
    """
    /api/health/ must never leak credentials, and must state plainly
    whether a shared database is in use.
    """

    def test_health_is_public(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_health_reports_the_database_in_use(self):
        data = self.client.get(reverse("health")).json()
        self.assertIn("db_engine", data)
        self.assertIn("is_postgres", data)
        self.assertIn("database_url_set", data)

    def test_health_never_exposes_secrets(self):
        body = self.client.get(reverse("health")).content.decode().lower()
        for secret in ("password", "postgres://", "postgresql://", "secret_key"):
            self.assertNotIn(secret, body)

    def test_instance_id_is_stable_within_process(self):
        first = self.client.get(reverse("health")).json()
        second = self.client.get(reverse("health")).json()
        self.assertEqual(first["instance"], second["instance"])

    def test_database_failure_returns_503_without_exception_details(self):
        with patch("shop_backend.health.connection.cursor", side_effect=RuntimeError("private-db-host")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["db_reachable"])
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertNotIn("private-db-host", response.content.decode())
