from rest_framework.permissions import BasePermission
from accounts.permissions import IsSponsor, IsSponsorOrLender


class IsMemorandumOwner(BasePermission):
    """Object-level: sponsor can only access their own memorandums."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.sponsor_id == request.user.id
