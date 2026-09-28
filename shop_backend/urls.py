from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

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
    # root opens swagger directly
    path(
        "",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui-root",
    ),
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
    # Always serve uploaded media files
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
