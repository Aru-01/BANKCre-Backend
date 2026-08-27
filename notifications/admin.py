from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from django.utils.translation import gettext_lazy as _

from notifications.models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = [
        "id",
        "recipient",
        "display_notification_type",
        "title",
        "display_is_read",
        "created_at",
    ]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = [
        "recipient__email",
        "recipient__first_name",
        "recipient__last_name",
        "title",
        "message",
    ]
    raw_id_fields = ["recipient"]
    date_hierarchy = "created_at"
    actions = ["action_mark_as_read", "action_mark_as_unread"]
    ordering = ["-created_at"]

    @display(
        description=_("Type"),
        label={
            "NEW_LOAN_REQUEST": "info",
            "LOAN_REQUEST_UPDATED": "warning",
            "NEW_QUOTE_RECEIVED": "purple",
            "QUOTE_ACCEPTED": "success",
            "QUOTE_DECLINED": "danger",
            "MEMORANDUM_READY": "success",
            "SYSTEM_ALERT": "neutral",
        },
    )
    def display_notification_type(self, obj):
        return obj.notification_type

    @display(description=_("Read Status"), boolean=True)
    def display_is_read(self, obj):
        return obj.is_read

    @action(description=_("Mark selected notifications as read"))
    def action_mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"{count} notification(s) marked as read.")

    @action(description=_("Mark selected notifications as unread"))
    def action_mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f"{count} notification(s) marked as unread.")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "display_quote_emails",
        "display_marketing_emails",
        "updated_at",
    ]
    list_filter = [
        "quote_emails_enabled",
        "marketing_emails_enabled",
    ]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]
    readonly_fields = ["updated_at"]
    ordering = ["-updated_at"]

    @display(description=_("Quote Emails"), boolean=True)
    def display_quote_emails(self, obj):
        return obj.quote_emails_enabled

    @display(description=_("Marketing Emails"), boolean=True)
    def display_marketing_emails(self, obj):
        return obj.marketing_emails_enabled
