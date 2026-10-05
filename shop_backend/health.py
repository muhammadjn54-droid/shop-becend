"""
Диагностический endpoint.

Показывает, какую базу данных реально использует сервер, не раскрывая
ни логина, ни пароля, ни адреса хоста. Нужен, чтобы отличить
"PostgreSQL настроен" от "приложение молча работает на /tmp SQLite",
из-за которого данные исчезали через несколько минут.
"""

import os
import uuid

from django.conf import settings
from django.db import connection
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

INSTANCE_ID = uuid.uuid4().hex[:8]


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def health(request):
    engine = connection.settings_dict["ENGINE"]
    is_postgres = "postgresql" in engine

    payload = {
        "status": "ok",
        "db_engine": engine,
        "is_postgres": is_postgres,
        "database_url_set": bool(os.environ.get("DATABASE_URL")),
        "is_vercel": bool(getattr(settings, "IS_VERCEL", False)),
        "is_render": bool(getattr(settings, "IS_RENDER", False)),
        # Different value on every serverless instance, so two parallel
        # requests returning different ids proves requests are not
        # hitting the same process.
        "instance": INSTANCE_ID,
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        payload["db_reachable"] = True
    except Exception:
        payload["db_reachable"] = False
        payload["status"] = "unavailable"

    return Response(payload, status=200 if payload["db_reachable"] else 503)
