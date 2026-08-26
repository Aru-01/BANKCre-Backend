from django.urls import path
from notifications.views import (
    NotificationListView,
    UnreadCountView,
    MarkAsReadView,
    MarkAllAsReadView,
    DeleteNotificationView,
    ClearAllNotificationsView,
    NotificationPreferenceView,
)

app_name = "notifications"

urlpatterns = [
    # List notifications
    path("", NotificationListView.as_view(), name="notification-list"),
    # Unread badge count
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
    # Bulk operations
    path("read-all/", MarkAllAsReadView.as_view(), name="mark-all-read"),
    path("clear-all/", ClearAllNotificationsView.as_view(), name="clear-all"),
    # Single notification operations
    path("<int:pk>/read/", MarkAsReadView.as_view(), name="mark-read"),
    path("<int:pk>/", DeleteNotificationView.as_view(), name="delete"),
    # Notification preferences
    path(
        "preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
]
