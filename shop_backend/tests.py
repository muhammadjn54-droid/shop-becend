from django.test import TestCase, override_settings
from django.urls import reverse


class ProductionSwaggerTests(TestCase):
    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["testserver"],
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
            },
        },
    )
    def test_swagger_root_renders_in_production_mode(self):
        response = self.client.get(reverse("schema-swagger-ui-root"))
        self.assertEqual(response.status_code, 200)
