from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
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
