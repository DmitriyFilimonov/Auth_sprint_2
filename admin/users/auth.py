from jwt import decode
import http
from enum import StrEnum, auto

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class Roles(StrEnum):
    ADMIN = auto()
    SUBSCRIBER = auto()


class CustomBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        url = settings.AUTH_API_LOGIN_URL
        payload = {"login": username, "password": password}
        response = requests.post(url, json=payload)
        if response.status_code != http.HTTPStatus.OK:
            return None

        data = response.json()

        access_token = data["access_token"]
        request.session["access_token"] = access_token
        request.session["refresh_token"] = data["refresh_token"]

        decoded = decode(jwt=access_token, options={"verify_signature": False})

        print(decoded)

        try:
            user, _created = User.objects.get_or_create(
                id=decoded["user_id"],
            )
            user.email = "fake@mail.domain"
            user.first_name = ""
            user.last_name = ""
            user.is_admin = decoded.get("role") == "superuser"
            user.is_active = decoded.get("role") == "superuser"
            user.save()

        except Exception:
            return None

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
