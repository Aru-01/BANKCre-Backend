from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from chatbot.models import Conversation, Message

User = get_user_model()


class ChatbotAPITests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="sponsor@test.com",
            password="password123",
            first_name="Sponsor",
            last_name="One",
            phone="1234567890",
        )
        self.user2 = User.objects.create_user(
            email="other@test.com",
            password="password123",
            first_name="Other",
            last_name="Two",
            phone="0987654321",
        )

    @patch("chatbot.views.get_chat_response")
    def test_send_chat_message_new_conversation(self, mock_get_chat_response):
        mock_get_chat_response.return_value = {
            "reply": "To generate a memorandum, navigate to the Memorandums section.",
            "conversation_history": [],
        }

        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/chatbot/chat/"
        data = {"message": "How do I generate a memorandum?"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("conversation_id", response.data["data"])
        self.assertIn("reply", response.data["data"])

        conv_id = response.data["data"]["conversation_id"]
        conv = Conversation.objects.get(id=conv_id)
        self.assertEqual(conv.user, self.user1)
        self.assertEqual(conv.title, "How do I generate a memorandum?")
        self.assertEqual(conv.messages.count(), 2)

    @patch("chatbot.views.get_chat_response")
    def test_send_chat_message_existing_conversation(self, mock_get_chat_response):
        conv = Conversation.objects.create(user=self.user1, title="Test Chat")
        mock_get_chat_response.return_value = {
            "reply": "Yes, you can edit in Editor Mode.",
            "conversation_history": [],
        }

        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/chatbot/chat/"
        data = {"message": "Can I edit it later?", "conversation_id": conv.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["conversation_id"], conv.id)
        self.assertEqual(conv.messages.count(), 2)

    def test_conversation_list_and_last_message(self):
        conv1 = Conversation.objects.create(user=self.user1, title="Chat 1")
        conv2 = Conversation.objects.create(user=self.user1, title="Chat 2")
        Conversation.objects.create(user=self.user2, title="Other User Chat")

        Message.objects.create(conversation=conv1, role="user", content="Msg 1")
        Message.objects.create(conversation=conv1, role="assistant", content="Msg 2")
        Message.objects.create(conversation=conv2, role="user", content="Msg 3")

        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/chatbot/conversations/"

        # Verify N+1 query is eliminated (1 query for conversations + 1 for prefetched messages)
        with self.assertNumQueries(2):
            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        # Check last message of conv1 is Msg 2
        conv1_data = next(c for c in response.data["data"] if c["id"] == conv1.id)
        self.assertIsNotNone(conv1_data["last_message"])
        self.assertEqual(conv1_data["last_message"]["content"], "Msg 2")

    def test_conversation_detail_and_permission(self):
        conv1 = Conversation.objects.create(user=self.user1, title="User1 Chat")
        Message.objects.create(conversation=conv1, role="user", content="Hello")
        Message.objects.create(
            conversation=conv1, role="assistant", content="Hi there!"
        )

        # User 1 can view via detail URL /<id>/
        self.client.force_authenticate(user=self.user1)
        url_detail = f"/api/v1/chatbot/conversations/{conv1.id}/"
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # User 2 gets 403 Forbidden
        self.client.force_authenticate(user=self.user2)
        response_forbidden = self.client.get(url_detail)
        self.assertEqual(response_forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_conversation(self):
        conv1 = Conversation.objects.create(user=self.user1, title="User1 Chat")

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/chatbot/conversations/{conv1.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Conversation.objects.filter(id=conv1.id).exists())
