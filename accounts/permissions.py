from rest_framework.permissions import BasePermission
from accounts.models import Role


class IsLender(BasePermission):
    message = "Lender access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_role(Role.LENDER)


class IsSponsor(BasePermission):
    message = "Sponsor access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_role(Role.SPONSOR)


class IsSponsorOrLender(BasePermission):
    message = "Sponsor or Lender access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.has_role(Role.SPONSOR) or request.user.has_role(Role.LENDER)
