from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="Shop Inventory API",
        default_version="v1",
        description=(
            "API для учёта товаров, склада и продаж. "
            "Позволяет добавлять товары, регистрировать продажи, "
            "отслеживать остатки, выручку, прибыль и убытки."
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # auth
    path("api/auth/", include("accounts.urls")),
    # products + sales + statistics + dashboard
    path("api/", include("products.urls")),
    path("api/", include("sales.urls")),
    # swagger / redoc
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
