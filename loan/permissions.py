from rest_framework.permissions import BasePermission
from accounts.permissions import IsSponsor, IsLender, IsSponsorOrLender

__all__ = [
    "IsSponsor",
    "IsLender",
    "IsSponsorOrLender",
    "IsLoanRequestOwner",
    "IsQuoteOwner",
    "CanViewQuote",
]


class IsLoanRequestOwner(BasePermission):
    message = "You do not have permission to modify this loan request."

    def has_object_permission(self, request, view, obj):
        return obj.sponsor_id == request.user.id


class IsQuoteOwner(BasePermission):
    message = "You do not have permission to modify this quote."

    def has_object_permission(self, request, view, obj):
        return obj.lender_id == request.user.id


class CanViewQuote(BasePermission):
    message = "You do not have permission to view this quote."

    def has_object_permission(self, request, view, obj):
        return (
            obj.lender_id == request.user.id
            or obj.loan_request.sponsor_id == request.user.id
        )
