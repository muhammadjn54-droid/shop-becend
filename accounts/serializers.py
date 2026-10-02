from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о текущем пользователе."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "date_joined")
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """
    Принимает username или email в одном поле, чтобы пользователю не
    приходилось запоминать, как именно он зарегистрировался.
    """

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        identifier = (attrs.get("username") or "").strip()
        password = attrs.get("password")

        user = (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
        )

        if not user or not user.check_password(password):
            raise serializers.ValidationError(
                {"detail": "Неверное имя пользователя или пароль"}
            )
        if not user.is_active:
            raise serializers.ValidationError({"detail": "Аккаунт отключён"})

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
