from django.contrib.admin import AdminSite

from users.auth_service import logout_from_auth_service


class CustomAdminSite(AdminSite):
    """Перед выходом из Django — сброс токенов в auth-service."""

    def logout(self, request, extra_context=None):
        logout_from_auth_service(request)
        return super().logout(request, extra_context)


admin_site = CustomAdminSite(name="admin")
