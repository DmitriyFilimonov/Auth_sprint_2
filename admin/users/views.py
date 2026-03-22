from django.shortcuts import render
import requests
from django.conf import settings
from clients.auth_api.auth_api_client.client import AuthenticatedClient


def login_history_view(request):
    page = request.GET.get("page", 1)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    AuthenticatedClient()

    params = {
        "page": page,
        "from": date_from,
        "to": date_to,
    }

    response = requests.get(
        f"{settings.AUTH_API_URL}/users/login-history",
        params=params,
    )

    data = response.json()

    return render(
        request,
        "admin/login_history.html",
        {
            "items": data["items"],
            "page": data["page"],
            "total_pages": data["total_pages"],
            "from": date_from,
            "to": date_to,
        },
    )
