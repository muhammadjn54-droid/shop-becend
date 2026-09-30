from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации нового пользователя."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Повтор пароля")

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"detail": "Пароли не совпадают"}
            )

        email = (attrs.get("email") or "").strip().lower()
        if not email:
            attrs["email"] = None
        else:
            attrs["email"] = email
            if User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    {"email": "Этот email уже занят"}
                )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email") or None,
            password=validated_data["password"],
        )
        return user


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
