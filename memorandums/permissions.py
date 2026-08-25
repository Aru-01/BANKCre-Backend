from rest_framework.permissions import BasePermission
from accounts.models import Role


class IsSponsor(BasePermission):
    """Allow access only to authenticated users who have the Sponsor role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.has_role(Role.SPONSOR)


class IsMemorandumOwner(BasePermission):
    """Object-level: sponsor can only access their own memorandums."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.sponsor_id == request.user.id
