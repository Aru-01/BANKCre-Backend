from rest_framework import serializers
from notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "created_at",
            "memorandum_id",
            "loan_request_id",
            "quote_id",
        ]
        read_only_fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "created_at",
            "memorandum_id",
            "loan_request_id",
            "quote_id",
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "quote_emails_enabled",
            "marketing_emails_enabled",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
