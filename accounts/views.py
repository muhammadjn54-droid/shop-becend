from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    LoginSerializer,
    UserSerializer,
    LogoutSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Вход пользователя по username ИЛИ по email, возвращает access и
    refresh токены. Если в поле username передан email, он
    преобразуется в username.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer



class MeView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/

    Возвращает информацию о текущем авторизованном пользователе.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Добавляет refresh token в чёрный список (blacklist),
    после чего им нельзя будет воспользоваться повторно.
    """

    permission_classes = [permissions.IsAuthenticated]

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
