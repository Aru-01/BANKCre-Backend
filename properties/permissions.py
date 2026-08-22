from rest_framework.permissions import BasePermission
from accounts.permissions import IsSponsor, IsLender  # reuse from accounts


__all__ = ['IsSponsor', 'IsLender', 'IsPropertyOwner']


class IsPropertyOwner(BasePermission):
    """
    Object-level permission: only the sponsor who owns the property
    can read/modify/delete it.
    """
    message = 'You do not have permission to access this property.'

    def has_object_permission(self, request, view, obj):
        # obj is a Property instance
        return obj.sponsor_id == request.user.id
