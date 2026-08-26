import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from chatbot.models import Conversation, Message
from chatbot.serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ChatSerializer,
    MessageSerializer,
)
from chatbot.ai_files.chatbot import get_chat_response

logger = logging.getLogger(__name__)


def _get_conversation(user, pk):
    """Helper to fetch a conversation and verify user ownership."""
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return None, Response(
            {"message": "Conversation not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if conversation.user != user:
        return None, Response(
            {"message": "You do not have permission to access this conversation."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return conversation, None


class ChatView(APIView):
    """
    POST /api/v1/chatbot/chat/
    Send a user message to the BANCre AI Assistant and receive an answer.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send a chat message to AI assistant",
        operation_description=(
            "Send a query to the BANCre AI Assistant for real estate Q&A or platform navigation. "
            "If `conversation_id` is provided, continues the chat thread; otherwise auto-creates a new conversation."
        ),
        tags=["Chatbot"],
        request_body=ChatSerializer,
        responses={
            201: openapi.Response(
                "Message sent and AI response received successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Message sent successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "conversation_id": openapi.Schema(
                                    type=openapi.TYPE_INTEGER, example=1
                                ),
                                "reply": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="To generate a memorandum...",
                                ),
                            },
                        ),
                    },
                ),
            ),
            400: "Validation error.",
            403: "Permission denied for this conversation.",
            503: "AI service temporarily unavailable.",
        },
    )
    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid request.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        # Resolve or create conversation
        if conversation_id:
            conversation, error = _get_conversation(request.user, conversation_id)
            if error:
                return error
            is_new = False
        else:
            conversation = Conversation.objects.create(user=request.user)
            is_new = True

        # Fetch existing messages once (oldest first)
        existing_messages = list(conversation.messages.order_by("created_at"))
        is_first_message = is_new or len(existing_messages) == 0
        conversation_history = [
            {"role": msg.role, "content": msg.content} for msg in existing_messages
        ]

        # Persist the user message
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        # Call OpenAI gpt-4o
        try:
            result = get_chat_response(user_message, conversation_history)
        except Exception as e:
            logger.error("AI service error in ChatView: %s", str(e), exc_info=True)
            return Response(
                {"message": "AI service is temporarily unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        reply = result.get("reply", "")

        # Persist assistant reply
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=reply,
        )

        # Auto-set title from the first 60 chars of opening message
        if is_first_message:
            conversation.title = user_message[:60].strip()

        conversation.save(update_fields=["title", "updated_at"])

        return Response(
            {
                "message": "Message sent successfully.",
                "data": {
                    "conversation_id": conversation.id,
                    "reply": reply,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationListView(APIView):
    """
    GET /api/v1/chatbot/conversations/
    List all chat conversations for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List user conversations",
        operation_description="Returns all conversation threads for the authenticated user ordered by most recently updated.",
        tags=["Chatbot"],
        responses={
            200: openapi.Response(
                "Conversations retrieved successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Conversations retrieved successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "title": openapi.Schema(type=openapi.TYPE_STRING),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                    "updated_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request):
        conversations = (
            Conversation.objects.filter(user=request.user)
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=Message.objects.order_by("-created_at", "-id"),
                    to_attr="prefetched_messages",
                )
            )
        )
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(
            {
                "message": "Conversations retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ConversationDetailView(APIView):
    """
    GET    /api/v1/chatbot/conversations/<pk>/  — Retrieve conversation message history
    DELETE /api/v1/chatbot/conversations/<pk>/  — Delete conversation
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get conversation details and messages",
        operation_description="Retrieve all chronological messages for a specific conversation thread.",
        tags=["Chatbot"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Conversation ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                "Messages retrieved successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Messages retrieved successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "role": openapi.Schema(
                                        type=openapi.TYPE_STRING, example="user"
                                    ),
                                    "content": openapi.Schema(type=openapi.TYPE_STRING),
                                    "created_at": openapi.Schema(
                                        type=openapi.TYPE_STRING, format="date-time"
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            403: "Permission denied.",
            404: "Conversation not found.",
        },
    )
    def get(self, request, pk):
        conversation, error = _get_conversation(request.user, pk)
        if error:
            return error

        messages = conversation.messages.order_by("created_at")
        serializer = MessageSerializer(messages, many=True)
        return Response(
            {
                "message": "Messages retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Delete a conversation",
        operation_description="Deletes a conversation thread and all of its associated messages.",
        tags=["Chatbot"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Conversation ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                "Conversation deleted successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Conversation deleted successfully.",
                        ),
                    },
                ),
            ),
            403: "Permission denied.",
            404: "Conversation not found.",
        },
    )
    def delete(self, request, pk):
        conversation, error = _get_conversation(request.user, pk)
        if error:
            return error
        conversation.delete()
        return Response(
            {"message": "Conversation deleted successfully."},
            status=status.HTTP_200_OK,
        )
