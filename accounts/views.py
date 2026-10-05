import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    LoginSerializer,
    SessionRefreshSerializer,
    RegisterSerializer,
    UserSerializer,
    LogoutSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginThrottle(AnonRateThrottle):
    scope = "auth_login"
    rate = "30/minute"


class RegisterThrottle(AnonRateThrottle):
    scope = "auth_register"
    rate = "10/minute"


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/

    Регистрация нового пользователя. После успешной регистрации
    сразу возвращает пару JWT токенов (access и refresh), чтобы
    фронтенд мог сразу авторизовать пользователя без повторного ввода логина.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Пользователь успешно зарегистрирован",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class PasswordResetThrottle(AnonRateThrottle):
    """Ограничивает частоту запросов на восстановление пароля."""

    scope = "password_reset"
    rate = "10/minute"


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/forgot-password/
    POST /api/auth/password-reset/

    Отправляет ссылку со сбросом пароля на указанный email.
    Всегда возвращает одинаковый ответ для защиты от перечисления пользователей.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    @swagger_auto_schema(request_body=PasswordResetRequestSerializer)
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        matches = list(User.objects.filter(email__iexact=email, is_active=True)[:2])
        user = matches[0] if len(matches) == 1 else None

        if user and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
            reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            subject = "Reset your password"
            message = (
                "Hello,\n\n"
                "We received a request to reset your password.\n\n"
                "Click the link below to create a new password:\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, you can ignore this email."
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.warning("SMTP email sending error: %s", type(e).__name__)

        return Response(
            {
                "message": "If an account with this email exists, a password reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/reset-password/
    POST /api/auth/password-reset-confirm/

    Устанавливает новый пароль после проверки токена.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    @swagger_auto_schema(request_body=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data["password"]
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=serializer.validated_data["user"].pk)
            if not default_token_generator.check_token(user, serializer.validated_data["token"]):
                raise serializers.ValidationError({"detail": "Invalid or expired reset token."})
            user.set_password(password)
            user.save(update_fields=["password"])

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )




class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Вход пользователя по username ИЛИ по email, возвращает access и
    refresh токены. Если в поле username передан email, он
    преобразуется в username.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]
    serializer_class = LoginSerializer



class SessionRefreshView(TokenRefreshView):
    authentication_classes = []
    serializer_class = SessionRefreshSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/auth/me/

    Возвращает информацию о текущем авторизованном пользователе.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Добавляет refresh token в чёрный список (blacklist),
    после чего им нельзя будет воспользоваться повторно.
    """

    # The refresh token itself authorizes revoking that token. An expired
    # access token must not stop a user from ending their session.
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @swagger_auto_schema(request_body=LogoutSerializer)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Недействительный refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Вы успешно вышли из системы"},
            status=status.HTTP_200_OK,
        )
