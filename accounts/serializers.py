from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

User = get_user_model()


def validate_username_available(value, instance=None):
    value = value.strip()
    users = User.objects.all()
    if instance is not None:
        users = users.exclude(pk=instance.pk)
    # Username and email share the same login input, so check both namespaces.
    if users.filter(Q(username__iexact=value) | Q(email__iexact=value)).exists():
        raise serializers.ValidationError("Этот логин уже занят")
    return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password2")
        read_only_fields = ("id",)

    def validate_username(self, value):
        return validate_username_available(value)

    def validate_email(self, value):
        email = (value or "").strip().lower() or None
        if email and User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exists():
            raise serializers.ValidationError("Этот email уже занят")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Пароли не совпадают"})
        validate_password(
            attrs["password"],
            user=User(username=attrs["username"], email=attrs.get("email")),
        )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        try:
            with transaction.atomic():
                return User.objects.create_user(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"detail": "Логин или email уже занят. Проверьте данные."}
            )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "email", "date_joined")

    def validate_username(self, value):
        return validate_username_available(value, instance=self.instance)

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                # Do not overwrite a simultaneous password reset with a stale
                # password loaded earlier in request.user.
                for name, value in validated_data.items():
                    setattr(instance, name, value)
                if validated_data:
                    instance.save(update_fields=list(validated_data))
                return instance
        except IntegrityError:
            raise serializers.ValidationError({"username": "Этот логин уже занят"})


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    def validate(self, attrs):
        identifier = attrs["username"].strip()
        matches = list(User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        )[:2])
        user = matches[0] if len(matches) == 1 else None
        if not user:
            User().set_password(attrs["password"])
        if not user or not user.check_password(attrs["password"]) or not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Неверное имя пользователя или пароль"}
            )
        refresh = RefreshToken.for_user(user)
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class SessionRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise InvalidToken("Сессия недействительна. Войдите снова.")
        if not user.is_active or refresh.get(
            api_settings.REVOKE_TOKEN_CLAIM
        ) != get_md5_hash_password(user.password):
            raise InvalidToken("Сессия недействительна. Войдите снова.")
        # Concurrent tabs use the same revocable refresh token. Its original
        # 30-day expiry is never extended.
        return {"access": str(refresh.access_token)}


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    def validate(self, attrs):
        password = attrs.get("password") or attrs.get("new_password")
        confirmation = attrs.get("confirm_password") or attrs.get("new_password2")
        if not password or not confirmation:
            raise serializers.ValidationError({"detail": "Password and confirmation are required."})
        if password != confirmation:
            raise serializers.ValidationError({"detail": "Passwords do not match."})
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.filter(pk=user_id, is_active=True).first()
        except (ValueError, TypeError, OverflowError, UnicodeDecodeError):
            user = None
        if not user or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"detail": "Invalid or expired reset token."})
        validate_password(password, user=user)
        attrs["user"] = user
        attrs["password"] = password
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(trim_whitespace=False)