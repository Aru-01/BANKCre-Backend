from django.contrib import admin
from notifications.models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "recipient",
        "notification_type",
        "title",
        "is_read",
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


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "quote_emails_enabled",
        "marketing_emails_enabled",
        "updated_at",
    ]
    list_filter = ["quote_emails_enabled", "marketing_emails_enabled"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user"]
