from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import Role, RoleModel
from properties.models import Property
from loan.models import LoanRequest, LoanQuote

User = get_user_model()


class LoanAppAPITests(APITestCase):
    def setUp(self):
        # Create Roles
        self.sponsor_role, _ = RoleModel.objects.get_or_create(name=Role.SPONSOR)
        self.lender_role, _ = RoleModel.objects.get_or_create(name=Role.LENDER)

        # Sponsor User
        self.sponsor = User.objects.create_user(
            email="sponsor@test.com",
            password="password123",
            first_name="Alice",
            last_name="Sponsor",
            phone="1111111111",
            active_role=Role.SPONSOR,
        )
        self.sponsor.roles.add(self.sponsor_role)

        # Lender User
        self.lender = User.objects.create_user(
            email="lender@test.com",
            password="password123",
            first_name="Bob",
            last_name="Lender",
            phone="2222222222",
            active_role=Role.LENDER,
        )
        self.lender.roles.add(self.lender_role)

        # Dual-Role User (both Sponsor & Lender)
        self.dual_user = User.objects.create_user(
            email="dual@test.com",
            password="password123",
            first_name="Charlie",
            last_name="Dual",
            phone="3333333333",
            active_role=Role.LENDER,
        )
        self.dual_user.roles.add(self.sponsor_role, self.lender_role)

        # Create Properties
        self.property_sponsor = Property.objects.create(
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            property_name="Sunset Plaza",
            property_address="100 Sunset Blvd, Austin, TX",
            property_type="Commercial",
            number_of_units=10,
            rentable_area=Decimal("15000.00"),
            year_built=2020,
            occupancy=Decimal("95.00"),
            parking_spaces=30,
            latitude=Decimal("30.2672"),
            longitude=Decimal("-97.7431"),
        )

        self.property_dual = Property.objects.create(
            sponsor=self.dual_user,
            sponsor_role=self.sponsor_role,
            property_name="Dual Tower",
            property_address="200 Main St, Dallas, TX",
            property_type="Office",
            number_of_units=20,
            rentable_area=Decimal("50000.00"),
            year_built=2022,
            occupancy=Decimal("90.00"),
            parking_spaces=100,
            latitude=Decimal("32.7767"),
            longitude=Decimal("-96.7970"),
        )

    def test_create_loan_request_by_sponsor(self):
        self.client.force_authenticate(user=self.sponsor)
        url = "/api/v1/loans/requests/"
        data = {
            "property": self.property_sponsor.id,
            "requested_amount": "5000000.00",
            "loan_term": 36,
            "ltv": "75.00",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["status"], "Active")
        self.assertEqual(response.data["data"]["requested_amount"], "5000000.00")

    def test_cannot_create_loan_request_for_other_user_property(self):
        self.client.force_authenticate(user=self.sponsor)
        url = "/api/v1/loans/requests/"
        # Attempting to create request on dual_user's property
        data = {
            "property": self.property_dual.id,
            "requested_amount": "1000000.00",
            "loan_term": 24,
            "ltv": "70.00",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("property", response.data["errors"])

    def test_lender_marketplace_excludes_own_property(self):
        # Create a loan request by sponsor
        req1 = LoanRequest.objects.create(
            property=self.property_sponsor,
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            requested_amount=Decimal("2000000.00"),
            loan_term=36,
            ltv=Decimal("70.00"),
            status="Active",
        )

        # Create a loan request by dual user on their own property
        req2 = LoanRequest.objects.create(
            property=self.property_dual,
            sponsor=self.dual_user,
            sponsor_role=self.sponsor_role,
            requested_amount=Decimal("4000000.00"),
            loan_term=48,
            ltv=Decimal("75.00"),
            status="Active",
        )

        # Dual user (active_role='Lender') views marketplace automatically
        self.client.force_authenticate(user=self.dual_user)
        url = "/api/v1/loans/requests/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [r["id"] for r in response.data["data"]]
        # Should see req1 (Sponsor's property)
        self.assertIn(req1.id, request_ids)
        # Should NOT see req2 (Dual user's own property)
        self.assertNotIn(req2.id, request_ids)

    def test_lender_submits_quote_and_self_quote_prevention(self):
        loan_request = LoanRequest.objects.create(
            property=self.property_sponsor,
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            requested_amount=Decimal("3000000.00"),
            loan_term=36,
            ltv=Decimal("70.00"),
            status="Active",
        )

        # Lender submits quote without lender_name (auto-derived from profile)
        self.client.force_authenticate(user=self.lender)
        url = f"/api/v1/loans/requests/{loan_request.id}/quotes/"
        quote_data = {
            "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "loan_amount": "3000000.00",
            "initial_funding": "2500000.00",
            "future_funding": "500000.00",
            "sponsor_equity": "1000000.00",
            "max_as_is_ltv": "70.00",
            "max_ltc": "75.00",
            "max_as_stabilized_ltv": "65.00",
            "min_as_is_dy": "9.50",
            "min_stabilized_dy": "10.50",
            "term": 36,
            "interest_rate": "6.50",
            "amortization": "30 Years",
            "prepayment": "Yield Maintenance",
            "origination_fee": "1.00",
            "capex_reserve": "50000.00",
            "ff_and_e_reserve": "25000.00",
            "interest_carry_reserve": "100000.00",
            "extension_conditions": "Subject to DSCR > 1.25",
            "collateral": "First Lien Deed of Trust",
            "recourse": "Non-Recourse with Standard Carveouts",
        }

        response = self.client.post(url, quote_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["status"], "Submitted")
        # Verify auto-derived lender_name from profile
        self.assertEqual(response.data["data"]["lender_name"], "Bob Lender")
        self.assertEqual(response.data["data"]["lender_email"], "lender@test.com")
        # Verify DSCR calculation: 9.5 / 6.5 = ~1.46
        self.assertEqual(response.data["data"]["dscr"], 1.46)

        # Test Self-Quoting Prevention: Sponsor attempts to submit quote on their own loan request
        self.client.force_authenticate(user=self.sponsor)
        response_self = self.client.post(url, quote_data, format="json")
        self.assertEqual(response_self.status_code, status.HTTP_403_FORBIDDEN)

    def test_accept_quote_flow(self):
        loan_request = LoanRequest.objects.create(
            property=self.property_sponsor,
            sponsor=self.sponsor,
            sponsor_role=self.sponsor_role,
            requested_amount=Decimal("3000000.00"),
            loan_term=36,
            ltv=Decimal("70.00"),
            status="Active",
        )

        future_exp = timezone.now() + timedelta(days=15)
        quote1 = LoanQuote.objects.create(
            loan_request=loan_request,
            lender=self.lender,
            lender_role=self.lender_role,
            lender_name="Lender 1",
            guarantor="G1",
            expires_at=future_exp,
            loan_amount=Decimal("3000000.00"),
            initial_funding=Decimal("3000000.00"),
            future_funding=Decimal("0.00"),
            sponsor_equity=Decimal("1000000.00"),
            max_as_is_ltv=Decimal("70.00"),
            max_ltc=Decimal("75.00"),
            max_as_stabilized_ltv=Decimal("65.00"),
            min_as_is_dy=Decimal("9.00"),
            min_stabilized_dy=Decimal("10.00"),
            term=36,
            interest_rate=Decimal("6.00"),
            amortization="30 yr",
            prepayment="None",
            origination_fee=Decimal("1.00"),
            capex_reserve=Decimal("0.00"),
            ff_and_e_reserve=Decimal("0.00"),
            interest_carry_reserve=Decimal("0.00"),
            extension_conditions="None",
            collateral="Deed",
            recourse="Non-recourse",
            status="Submitted",
        )

        quote2 = LoanQuote.objects.create(
            loan_request=loan_request,
            lender=self.dual_user,
            lender_role=self.lender_role,
            lender_name="Lender 2",
            guarantor="G2",
            expires_at=future_exp,
            loan_amount=Decimal("2900000.00"),
            initial_funding=Decimal("2900000.00"),
            future_funding=Decimal("0.00"),
            sponsor_equity=Decimal("1100000.00"),
            max_as_is_ltv=Decimal("68.00"),
            max_ltc=Decimal("72.00"),
            max_as_stabilized_ltv=Decimal("63.00"),
            min_as_is_dy=Decimal("9.20"),
            min_stabilized_dy=Decimal("10.20"),
            term=36,
            interest_rate=Decimal("6.25"),
            amortization="30 yr",
            prepayment="None",
            origination_fee=Decimal("1.00"),
            capex_reserve=Decimal("0.00"),
            ff_and_e_reserve=Decimal("0.00"),
            interest_carry_reserve=Decimal("0.00"),
            extension_conditions="None",
            collateral="Deed",
            recourse="Non-recourse",
            status="Submitted",
        )

        # Sponsor accepts quote1
        self.client.force_authenticate(user=self.sponsor)
        url_accept = f"/api/v1/loans/quotes/{quote1.id}/accept/"
        response = self.client.post(url_accept)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify quote1 is Accepted
        quote1.refresh_from_db()
        self.assertEqual(quote1.status, "Accepted")

        # Verify quote2 is Declined
        quote2.refresh_from_db()
        self.assertEqual(quote2.status, "Declined")

        # Verify loan_request is Closed
        loan_request.refresh_from_db()
        self.assertEqual(loan_request.status, "Closed")

    def test_dashboards(self):
        # Sponsor Dashboard
        self.client.force_authenticate(user=self.sponsor)
        url_sponsor_dash = "/api/v1/loans/dashboard/sponsor/"
        resp_sponsor = self.client.get(url_sponsor_dash)
        self.assertEqual(resp_sponsor.status_code, status.HTTP_200_OK)
        self.assertIn("header_stats", resp_sponsor.data["data"])
        self.assertIn("quote_comparison", resp_sponsor.data["data"])

        # Lender Dashboard
        self.client.force_authenticate(user=self.lender)
        url_lender_dash = "/api/v1/loans/dashboard/lender/"
        resp_lender = self.client.get(url_lender_dash)
        self.assertEqual(resp_lender.status_code, status.HTTP_200_OK)
        self.assertIn("header_stats", resp_lender.data["data"])
        self.assertIn("available_loan_requests", resp_lender.data["data"])
