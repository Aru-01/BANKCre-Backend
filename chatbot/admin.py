# chatbot/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from chatbot.models import Conversation, Message


class MessageInline(TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content", "created_at"]
    can_delete = True


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ["id", "user", "title", "created_at", "updated_at"]
    search_fields = ["user__email", "title"]
    list_filter = ["created_at", "updated_at"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ["id", "conversation", "role", "short_content", "created_at"]
    search_fields = ["content", "conversation__user__email", "conversation__title"]
    list_filter = ["role", "created_at"]

    def short_content(self, obj):
        return obj.content[:60] if obj.content else ""

    short_content.short_description = "Content"
