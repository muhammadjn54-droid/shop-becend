from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Кастомный пользователь. На старте ничего не добавляем сверх
    стандартных полей Django (username, email, password и т.д.),
    но модель своя — чтобы можно было расширять её в будущем
    без сложных миграций.
    """

    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.username
