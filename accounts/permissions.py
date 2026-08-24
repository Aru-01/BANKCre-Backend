from rest_framework.permissions import BasePermission
from accounts.models import Role



class IsLender(BasePermission):
    message = "Lender access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
            
        if not hasattr(request.user, '_is_lender_cache'):
            request.user._is_lender_cache = request.user.roles.filter(name=Role.LENDER).exists()
        return request.user._is_lender_cache


class IsSponsor(BasePermission):
    message = "Sponsor access is required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
            
        if not hasattr(request.user, '_is_sponsor_cache'):
            request.user._is_sponsor_cache = request.user.roles.filter(name=Role.SPONSOR).exists()
        return request.user._is_sponsor_cache
