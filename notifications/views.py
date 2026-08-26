from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
)
from notifications.permissions import IsRecipient


class NotificationListView(APIView):
    """
    GET /api/v1/notifications/ — List all notifications for the authenticated user
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List notifications",
        operation_description="Returns all in-app notifications for the logged-in user ordered by newest first. Optional query parameter `is_read` to filter.",
        tags=["Notifications"],
        manual_parameters=[
            openapi.Parameter(
                "is_read",
                openapi.IN_QUERY,
                description="Filter by read status (true or false)",
                type=openapi.TYPE_BOOLEAN,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response("Notifications retrieved successfully."),
        },
    )
    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user)

        is_read_param = request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                queryset = queryset.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                queryset = queryset.filter(is_read=False)

        serializer = NotificationSerializer(queryset, many=True)
        return Response(
            {
                "message": "Notifications retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class UnreadCountView(APIView):
    """
    GET /api/v1/notifications/unread-count/ — Returns unread notification count for badge display
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get unread notifications count",
        operation_description="Returns the total number of unread notifications for the user's notification bell icon badge.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Unread count retrieved successfully."),
        },
    )
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response(
            {
                "message": "Unread count retrieved successfully.",
                "data": {"unread_count": count},
            },
            status=status.HTTP_200_OK,
        )


class MarkAsReadView(APIView):
    """
    PATCH /api/v1/notifications/<pk>/read/ — Mark a single notification as read
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark single notification as read",
        operation_description="Marks an unread notification as read.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Notification marked as read."),
            403: "Permission denied.",
            404: "Notification not found.",
        },
    )
    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)

        if not IsRecipient().has_object_permission(request, self, notification):
            return Response(
                {"message": "You do not have permission to access this notification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        serializer = NotificationSerializer(notification)
        return Response(
            {
                "message": "Notification marked as read.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MarkAllAsReadView(APIView):
    """
    PATCH /api/v1/notifications/read-all/ — Mark all notifications as read in bulk
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Mark all notifications as read",
        operation_description="Bulk updates all unread notifications for the user to read status.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Notifications marked as read."),
        },
    )
    def patch(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response(
            {
                "message": f"{updated} notification(s) marked as read.",
                "data": {"updated_count": updated},
            },
            status=status.HTTP_200_OK,
        )


class DeleteNotificationView(APIView):
    """
    DELETE /api/v1/notifications/<pk>/ — Delete a single notification
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Delete a single notification",
        operation_description="Deletes a notification from user's notification list.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Notification deleted successfully."),
            403: "Permission denied.",
            404: "Notification not found.",
        },
    )
    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)

        if not IsRecipient().has_object_permission(request, self, notification):
            return Response(
                {"message": "You do not have permission to delete this notification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        notification.delete()
        return Response(
            {"message": "Notification deleted successfully."},
            status=status.HTTP_200_OK,
        )


class ClearAllNotificationsView(APIView):
    """
    DELETE /api/v1/notifications/clear-all/ — Clear all notifications for the authenticated user
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Clear all notifications",
        operation_description="Deletes all notifications for the authenticated user.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Notifications cleared successfully."),
        },
    )
    def delete(self, request):
        deleted_count, _ = Notification.objects.filter(
            recipient=request.user
        ).delete()
        return Response(
            {
                "message": f"{deleted_count} notification(s) cleared.",
                "data": {"deleted_count": deleted_count},
            },
            status=status.HTTP_200_OK,
        )


class NotificationPreferenceView(APIView):
    """
    GET   /api/v1/notifications/preferences/ — View notification preferences
    PATCH /api/v1/notifications/preferences/ — Update notification preferences
    """

    permission_classes = [IsAuthenticated]

    def _get_or_create_preference(self, user):
        preference, _ = NotificationPreference.objects.get_or_create(user=user)
        return preference

    @swagger_auto_schema(
        operation_summary="Get notification preferences",
        operation_description="Returns email and alert preferences for the user.",
        tags=["Notifications"],
        responses={
            200: openapi.Response("Notification preferences retrieved successfully."),
        },
    )
    def get(self, request):
        preference = self._get_or_create_preference(request.user)
        serializer = NotificationPreferenceSerializer(preference)
        return Response(
            {
                "message": "Notification preference retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Update notification preferences",
        operation_description="Update email alert toggles (e.g. quote emails enabled/disabled).",
        tags=["Notifications"],
        request_body=NotificationPreferenceSerializer,
        responses={
            200: openapi.Response("Notification preference updated successfully."),
            400: "Validation error.",
        },
    )
    def patch(self, request):
        preference = self._get_or_create_preference(request.user)
        serializer = NotificationPreferenceSerializer(
            preference, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {
                    "message": "Failed to update notification preference.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(
            {
                "message": "Notification preference updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
