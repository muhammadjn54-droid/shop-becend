from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    SessionRefreshView,
    MeView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", SessionRefreshView.as_view(), name="auth-token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("forgot-password/", PasswordResetRequestView.as_view(), name="auth-forgot-password"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("reset-password/", PasswordResetConfirmView.as_view(), name="auth-reset-password"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
]
