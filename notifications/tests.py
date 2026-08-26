from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import Role, RoleModel
from properties.models import Property
from loan.models import LoanRequest, LoanQuote
from notifications.models import Notification, NotificationPreference

User = get_user_model()


class NotificationAppAPITests(APITestCase):
    def setUp(self):
        # Roles
        self.sponsor_role, _ = RoleModel.objects.get_or_create(name=Role.SPONSOR)
        self.lender_role, _ = RoleModel.objects.get_or_create(name=Role.LENDER)

        # Users
        self.sponsor = User.objects.create_user(
            email="sponsor_notify@test.com",
            password="password123",
            first_name="Alice",
            last_name="Sponsor",
            phone="1111111111",
            active_role=Role.SPONSOR,
        )
        self.sponsor.roles.add(self.sponsor_role)

        self.lender = User.objects.create_user(
            email="lender_notify@test.com",
            password="password123",
            first_name="Bob",
            last_name="Lender",
            phone="2222222222",
            active_role=Role.LENDER,
        )
        self.lender.roles.add(self.lender_role)

        self.other_user = User.objects.create_user(
            email="other_notify@test.com",
            password="password123",
            first_name="Eve",
            last_name="Other",
            phone="3333333333",
            active_role=Role.SPONSOR,
        )

        # Property
        self.property = Property.objects.create(
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            property_name="Ocean View Plaza",
            property_address="500 Ocean Ave, Miami, FL",
            property_type="Commercial",
            number_of_units=15,
            rentable_area=Decimal("20000.00"),
            year_built=2021,
            occupancy=Decimal("92.00"),
            parking_spaces=40,
            latitude=Decimal("25.7617"),
            longitude=Decimal("-80.1918"),
        )

    def test_notification_list_and_unread_count(self):
        # Create notifications for sponsor
        n1 = Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            title="Notification 1",
            message="Message 1",
            is_read=False,
        )
        n2 = Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.QUOTE_SUBMITTED,
            title="Notification 2",
            message="Message 2",
            is_read=True,
        )

        self.client.force_authenticate(user=self.sponsor)

        # Check list
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)

        # Check unread filter
        response_unread = self.client.get("/api/v1/notifications/?is_read=false")
        self.assertEqual(response_unread.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_unread.data["data"]), 1)
        self.assertEqual(response_unread.data["data"][0]["id"], n1.id)

        # Check unread count
        response_count = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(response_count.status_code, status.HTTP_200_OK)
        self.assertEqual(response_count.data["data"]["unread_count"], 1)

    def test_mark_as_read_and_mark_all_read(self):
        n1 = Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            title="Notification 1",
            message="Message 1",
            is_read=False,
        )
        n2 = Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.QUOTE_SUBMITTED,
            title="Notification 2",
            message="Message 2",
            is_read=False,
        )

        self.client.force_authenticate(user=self.sponsor)

        # Mark single as read
        resp1 = self.client.patch(f"/api/v1/notifications/{n1.id}/read/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)

        # Mark all as read
        resp2 = self.client.patch("/api/v1/notifications/read-all/")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        n2.refresh_from_db()
        self.assertTrue(n2.is_read)

    def test_delete_notification_and_permission_isolation(self):
        n1 = Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            title="Notification 1",
            message="Message 1",
            is_read=False,
        )

        # Other user cannot access or delete sponsor's notification
        self.client.force_authenticate(user=self.other_user)
        resp_forbidden = self.client.delete(f"/api/v1/notifications/{n1.id}/")
        self.assertEqual(resp_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Sponsor can delete their own notification
        self.client.force_authenticate(user=self.sponsor)
        resp_del = self.client.delete(f"/api/v1/notifications/{n1.id}/")
        self.assertEqual(resp_del.status_code, status.HTTP_200_OK)
        self.assertFalse(Notification.objects.filter(id=n1.id).exists())

    def test_clear_all_notifications(self):
        Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            title="Notification 1",
            message="Message 1",
        )
        Notification.objects.create(
            recipient=self.sponsor,
            notification_type=Notification.QUOTE_SUBMITTED,
            title="Notification 2",
            message="Message 2",
        )

        self.client.force_authenticate(user=self.sponsor)
        resp = self.client.delete("/api/v1/notifications/clear-all/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(recipient=self.sponsor).count(), 0)

    def test_notification_preferences(self):
        self.client.force_authenticate(user=self.sponsor)

        # Retrieve preferences
        resp = self.client.get("/api/v1/notifications/preferences/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["data"]["quote_emails_enabled"])

        # Update preference to False
        resp_patch = self.client.patch(
            "/api/v1/notifications/preferences/",
            {"quote_emails_enabled": False},
            format="json",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(resp_patch.data["data"]["quote_emails_enabled"])

        pref = NotificationPreference.objects.get(user=self.sponsor)
        self.assertFalse(pref.quote_emails_enabled)

    def test_automated_signals_integration(self):
        # 1. Sponsor creates a LoanRequest -> Lender receives a notification
        initial_lender_notifications = Notification.objects.filter(recipient=self.lender).count()

        loan_request = LoanRequest.objects.create(
            property=self.property,
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            requested_amount=Decimal("3000000.00"),
            loan_term=36,
            ltv=Decimal("70.00"),
            status="Active",
        )

        lender_notifications = Notification.objects.filter(
            recipient=self.lender,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            loan_request_id=loan_request.id,
        )
        self.assertTrue(lender_notifications.exists())

        # 2. Lender submits a quote -> Sponsor receives a notification
        quote = LoanQuote.objects.create(
            loan_request=loan_request,
            lender=self.lender,
            lender_role=self.lender_role,
            lender_name="Apex Lender",
            guarantor="Apex Corp",
            expires_at=timezone.now() + timedelta(days=30),
            loan_amount=Decimal("3000000.00"),
            initial_funding=Decimal("3000000.00"),
            future_funding=Decimal("0.00"),
            sponsor_equity=Decimal("1000000.00"),
            max_as_is_ltv=Decimal("70.00"),
            max_ltc=Decimal("75.00"),
            max_as_stabilized_ltv=Decimal("65.00"),
            min_as_is_dy=Decimal("9.50"),
            min_stabilized_dy=Decimal("10.50"),
            term=36,
            interest_rate=Decimal("6.50"),
            amortization="30 Years",
            prepayment="None",
            origination_fee=Decimal("1.00"),
            capex_reserve=Decimal("0.00"),
            ff_and_e_reserve=Decimal("0.00"),
            interest_carry_reserve=Decimal("0.00"),
            extension_conditions="None",
            collateral="Deed",
            recourse="Non-Recourse",
            status="Submitted",
        )

        sponsor_notifications = Notification.objects.filter(
            recipient=self.sponsor,
            notification_type=Notification.QUOTE_SUBMITTED,
            quote_id=quote.id,
        )
        self.assertTrue(sponsor_notifications.exists())

        # 3. Quote is accepted -> Lender receives an acceptance notification
        quote.status = "Accepted"
        quote.save()

        accepted_notifications = Notification.objects.filter(
            recipient=self.lender,
            notification_type=Notification.QUOTE_ACCEPTED,
            quote_id=quote.id,
        )
        self.assertTrue(accepted_notifications.exists())
