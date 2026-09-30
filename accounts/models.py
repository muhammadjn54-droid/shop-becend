from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """
    Стандартный normalize_email превращает None в пустую строку
    (email = email or ""). С уникальным email две пустые строки
    конфликтуют, поэтому аккаунты без адреса нельзя было создать
    больше одного. Здесь пустое значение остаётся None, а в SQL
    несколько NULL не конфликтуют.
    """

    use_in_migrations = True

    def normalize_email(self, email):
        if not email:
            return None
        return super().normalize_email(email)


class CustomUser(AbstractUser):
    """
    Кастомный пользователь. На старте ничего не добавляем сверх
    стандартных полей Django (username, email, password и т.д.),
    но модель своя — чтобы можно было расширять её в будущем
    без сложных миграций.

    email уникален: без этого любой мог зарегистрироваться на чужой
    адрес и войти в аккаунт. Пустое значение хранится как NULL, потому
    что в SQL несколько NULL не конфликтуют, а несколько '' — конфликтуют.
    """

    email = models.EmailField(blank=True, null=True, unique=True)

    objects = UserManager()

    def __str__(self):
        return self.username
