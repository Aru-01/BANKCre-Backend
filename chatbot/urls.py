from django.urls import path
from chatbot.views import (
    ChatView,
    ConversationListView,
    ConversationDetailView,
)

app_name = "chatbot"

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
]
