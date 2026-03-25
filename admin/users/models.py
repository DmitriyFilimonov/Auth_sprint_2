import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from django.contrib.auth.base_user import BaseUserManager


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(verbose_name="email address", max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = True
    is_admin = models.BooleanField(default=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    # строка с именем поля модели, которая используется в качестве уникального идентификатора
    USERNAME_FIELD = "email"

    # менеджер модели
    objects = MyUserManager()

    def __str__(self):
        return f"{self.email} {self.id}"

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


class LoginHistory(models.Model):
    # Добавляем фиктивные поля, чтобы Django Admin знал, что отображать в колонках
    # primary_key=True обязателен для работы ссылок в админке
    id = models.CharField(max_length=255, primary_key=True)
    user_id = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False  # Чтобы Django не создавал таблицу в БД
        app_label = "users"
        verbose_name = "Запись из истории входов"
        verbose_name_plural = "История входов"

    def __str__(self):
        return f"{self.user_id} @ {self.created_at}"


class FilmListing(models.Model):
    """Прокси для отображения каталога из FastAPI; таблица в БД не используется."""

    uuid = models.CharField(max_length=36, primary_key=True)
    title = models.CharField(max_length=500)
    imdb_rating = models.FloatField(null=True, blank=True)
    genres_display = models.CharField(max_length=2000, blank=True)

    class Meta:
        managed = False
        app_label = "users"
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"

    def __str__(self):
        return self.title
