from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    LogoutSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/

    Регистрация нового пользователя. После успешной регистрации
    сразу возвращает пару JWT токенов (access и refresh), чтобы
    фронтенд мог сразу авторизовать пользователя.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

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
