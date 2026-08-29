from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from django.utils.translation import gettext_lazy as _

from loan.models import LoanRequest, LoanQuote


class LoanQuoteInline(TabularInline):
    model = LoanQuote
    extra = 0
    fields = [
        "lender_name",
        "lender",
        "loan_amount",
        "interest_rate",
        "term",
        "status",
        "expires_at",
    ]
    readonly_fields = ["lender", "expires_at"]
    ordering = ["-submitted_at"]


@admin.register(LoanRequest)
class LoanRequestAdmin(ModelAdmin):
    show_full_result_count = False
    list_display = [
        "id",
        "property",
        "sponsor",
        "display_requested_amount",
        "loan_term",
        "display_ltv",
        "display_status",
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
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["property", "sponsor", "sponsor_role"]
    list_select_related = ["property", "sponsor", "sponsor_role"]
    date_hierarchy = "created_at"
    inlines = [LoanQuoteInline]
    actions = ["action_mark_active", "action_mark_closed"]
    ordering = ["-created_at"]

    @display(
        description=_("Status"),
        label={
            "Active": "success",
            "Under Review": "warning",
            "Closed": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description=_("Requested Amount"))
    def display_requested_amount(self, obj):
        return f"${obj.requested_amount:,.2f}"

    @display(description=_("LTV"))
    def display_ltv(self, obj):
        return f"{obj.ltv}%"

    @action(description=_("Mark selected requests as Active"))
    def action_mark_active(self, request, queryset):
        count = queryset.update(status=LoanRequest.STATUS_ACTIVE)
        self.message_user(request, f"{count} loan request(s) marked as Active.")

    @action(description=_("Mark selected requests as Closed"))
    def action_mark_closed(self, request, queryset):
        count = queryset.update(status=LoanRequest.STATUS_CLOSED)
        self.message_user(request, f"{count} loan request(s) marked as Closed.")


@admin.register(LoanQuote)
class LoanQuoteAdmin(ModelAdmin):
    show_full_result_count = False
    list_display = [
        "id",
        "loan_request",
        "lender_name",
        "lender",
        "display_loan_amount",
        "display_interest_rate",
        "term",
        "display_status",
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
    list_select_related = ["loan_request__property", "lender", "lender_role"]
    readonly_fields = ["submitted_at", "updated_at"]
    date_hierarchy = "submitted_at"
    ordering = ["-submitted_at"]

    @display(
        description=_("Quote Status"),
        label={
            "Submitted": "info",
            "Under Review": "warning",
            "Accepted": "success",
            "Declined": "danger",
            "Expired": "neutral",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(description=_("Loan Amount"))
    def display_loan_amount(self, obj):
        return f"${obj.loan_amount:,.2f}"

    @display(description=_("Rate"))
    def display_interest_rate(self, obj):
        return f"{obj.interest_rate}%"
