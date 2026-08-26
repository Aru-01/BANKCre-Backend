from rest_framework import serializers
from chatbot.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "last_message"]

    def get_last_message(self, obj):
        prefetched = getattr(obj, "prefetched_messages", None)
        if prefetched is not None:
            last_msg = prefetched[0] if prefetched else None
        else:
            last_msg = obj.messages.order_by("-created_at", "-id").first()

        if last_msg:
            return {
                "id": last_msg.id,
                "role": last_msg.role,
                "content": last_msg.content[:100],
                "created_at": last_msg.created_at,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "messages"]


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="User's query or prompt for the AI assistant.",
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional ID of existing conversation. If omitted, a new conversation will be created.",
    )
