from rest_framework.permissions import BasePermission
from accounts.models import Role



class IsLender(BasePermission):
    message = "Lender access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name=Role.LENDER).exists()


class IsSponsor(BasePermission):
    message = "Sponsor access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name=Role.SPONSOR).exists()
