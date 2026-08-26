from django.contrib import admin
from loan.models import LoanRequest, LoanQuote


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "property",
        "sponsor",
        "requested_amount",
        "loan_term",
        "ltv",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "property__property_name",
        "property__property_address",
        "sponsor__email",
        "sponsor__first_name",
        "sponsor__last_name",
    ]
    raw_id_fields = ["property", "sponsor", "sponsor_role"]
    date_hierarchy = "created_at"


@admin.register(LoanQuote)
class LoanQuoteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "loan_request",
        "lender_name",
        "lender",
        "loan_amount",
        "interest_rate",
        "term",
        "status",
        "expires_at",
        "submitted_at",
    ]
    list_filter = ["status", "submitted_at", "expires_at"]
    search_fields = [
        "lender_name",
        "guarantor",
        "lender__email",
        "loan_request__property__property_name",
    ]
    raw_id_fields = ["loan_request", "lender", "lender_role"]
    date_hierarchy = "submitted_at"
