import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from properties.models import Property, PropertyChatSession, PropertyChatMessage
from properties.serializers import (
    PropertyChatSessionSerializer,
    PropertyChatMessageSerializer,
    PropertyChatInputSerializer,
)
from properties.chatbot import ask
from properties.views.schemas import success_schema, error_schema

logger = logging.getLogger(__name__)


class PropertyChatView(APIView):
    """
    Send a chat message about a property.
    ALL uploaded documents for the property are automatically used as AI context.
    No per-document selection needed — just select a property and chat.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send a chat message about a property",
        tags=["Property Chat"],
        request_body=PropertyChatInputSerializer,
        responses={
            201: openapi.Response(
                "Message sent successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "session_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "reply": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: error_schema("Invalid request."),
            503: error_schema("AI service unavailable."),
        },
    )
    def post(self, request, property_pk):
        prop = get_object_or_404(
            Property.objects.only("id", "property_name"), pk=property_pk
        )

        serializer = PropertyChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid request.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_message = serializer.validated_data["message"]
        session_id = serializer.validated_data.get("session_id")

        # ── Resolve or create session ───────────────────────────
        if session_id:
            session = get_object_or_404(
                PropertyChatSession.objects.select_related("user"),
                pk=session_id,
                property=prop,
            )
            if session.user_id != request.user.id and not request.user.is_superuser:
                return Response(
                    {"detail": "You do not have permission to access this session."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            session = PropertyChatSession.objects.create(
                property=prop, user=request.user
            )

        # Build history BEFORE saving the new user message (correct order)
        history = list(
            session.messages.order_by("created_at").values("role", "content")
        )

        # Persist user message
        PropertyChatMessage.objects.create(
            session=session, role="user", content=user_message
        )

        # ── Call AI ─────────────────────────────────────────────
        try:
            reply = ask(prop.id, user_message, history)
        except RuntimeError:
            return Response(
                {
                    "message": "AI service is temporarily unavailable. Please try again later."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected chatbot error: %s", exc)
            return Response(
                {"message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist assistant reply
        PropertyChatMessage.objects.create(
            session=session, role="assistant", content=reply
        )

        # Auto-set title from first user message
        if not history:
            session.title = user_message[:60].strip()
        session.save(update_fields=["title", "updated_at"])

        return Response(
            {
                "message": "Message sent successfully.",
                "session_id": session.id,
                "reply": reply,
            },
            status=status.HTTP_201_CREATED,
        )


class PropertyChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List chat sessions for a property",
        tags=["Property Chat"],
        responses={200: success_schema("Chat sessions retrieved successfully.")},
    )
    def get(self, request, property_pk):
        prop = get_object_or_404(Property.objects.only("id"), pk=property_pk)

        sessions = PropertyChatSession.objects.filter(property=prop)
        if not request.user.is_superuser:
            sessions = sessions.filter(user=request.user)

        sessions = sessions.only(
            "id", "property_id", "title", "created_at", "updated_at"
        ).order_by("-updated_at")
        return Response(
            {
                "message": "Chat sessions retrieved successfully.",
                "data": PropertyChatSessionSerializer(sessions, many=True).data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Create a new chat session",
        tags=["Property Chat"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "title": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Optional title"
                )
            },
        ),
        responses={201: success_schema("Chat session created successfully.")},
    )
    def post(self, request, property_pk):
        prop = get_object_or_404(Property.objects.only("id"), pk=property_pk)
        session = PropertyChatSession.objects.create(
            property=prop,
            user=request.user,
            title=request.data.get("title", "").strip() or "New Chat",
        )
        return Response(
            {
                "message": "Chat session created successfully.",
                "data": PropertyChatSessionSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PropertyChatSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_session(self, request, property_pk, session_id):
        prop = get_object_or_404(Property.objects.only("id"), pk=property_pk)
        session = get_object_or_404(
            PropertyChatSession.objects.select_related("user"),
            pk=session_id,
            property=prop,
        )
        if session.user_id != request.user.id and not request.user.is_superuser:
            return None, Response(
                {"detail": "You do not have permission to access this session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return session, None

    @swagger_auto_schema(
        operation_summary="Get messages in a chat session",
        tags=["Property Chat"],
        responses={
            200: success_schema("Messages retrieved successfully."),
            403: error_schema("Permission denied."),
        },
    )
    def get(self, request, property_pk, session_id):
        session, err = self._get_session(request, property_pk, session_id)
        if err:
            return err
        return Response(
            {
                "message": "Messages retrieved successfully.",
                "data": PropertyChatMessageSerializer(
                    session.messages.all(), many=True
                ).data,
            }
        )

    @swagger_auto_schema(
        operation_summary="Delete a chat session",
        tags=["Property Chat"],
        responses={
            200: success_schema("Chat session deleted successfully."),
            403: error_schema("Permission denied."),
        },
    )
    def delete(self, request, property_pk, session_id):
        session, err = self._get_session(request, property_pk, session_id)
        if err:
            return err
        session.delete()
        return Response({"message": "Chat session deleted successfully."})
