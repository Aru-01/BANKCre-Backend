from django.utils import timezone
from rest_framework import serializers
from loan.models import LoanRequest, LoanQuote


def _compute_dscr(quote):
    """
    Compute Debt Service Coverage Ratio (DSCR):
    DSCR = NOI / Annual Debt Service
    where:
      NOI = loan_amount * (min_as_is_dy / 100)
      Annual Debt Service = loan_amount * (interest_rate / 100)
    """
    try:
        loan_amount = float(quote.loan_amount)
        interest_rate = float(quote.interest_rate)
        min_as_is_dy = float(quote.min_as_is_dy)
        if interest_rate <= 0 or loan_amount <= 0:
            return None
        noi = loan_amount * (min_as_is_dy / 100.0)
        annual_debt_service = loan_amount * (interest_rate / 100.0)
        return round(noi / annual_debt_service, 2)
    except (TypeError, ValueError, ZeroDivisionError, AttributeError):
        return None


class LoanQuoteCreateSerializer(serializers.ModelSerializer):
    lender_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional lender name. If omitted, automatically derived from lender profile/company.",
    )
    guarantor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional guarantor. Defaults to company name or lender name.",
    )

    class Meta:
        model = LoanQuote
        fields = [
            "lender_name",
            "guarantor",
            "expires_at",
            "loan_amount",
            "initial_funding",
            "future_funding",
            "sponsor_equity",
            "max_as_is_ltv",
            "max_ltc",
            "max_as_stabilized_ltv",
            "min_as_is_dy",
            "min_stabilized_dy",
            "term",
            "interest_rate",
            "amortization",
            "prepayment",
            "origination_fee",
            "capex_reserve",
            "ff_and_e_reserve",
            "interest_carry_reserve",
            "extension_conditions",
            "collateral",
            "recourse",
        ]

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value

    def validate(self, data):
        loan_request = self.context.get("loan_request")
        request = self.context.get("request")

        if loan_request:
            # Prevent self-quoting: Lender cannot quote on their own property/loan request
            if request and (
                loan_request.sponsor_id == request.user.id
                or loan_request.property.sponsor_id == request.user.id
            ):
                raise serializers.ValidationError(
                    "You cannot submit a loan quote on your own property or loan request."
                )

            if loan_request.status != LoanRequest.STATUS_ACTIVE:
                raise serializers.ValidationError(
                    "Quotes can only be submitted for Active loan requests."
                )

        # Auto-derive lender_name and guarantor if omitted
        if request and request.user:
            full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            fallback_name = request.user.company_name or full_name or request.user.email
            if not data.get("lender_name"):
                data["lender_name"] = fallback_name
            if not data.get("guarantor"):
                data["guarantor"] = request.user.company_name or fallback_name

        return data


class LoanQuoteSerializer(serializers.ModelSerializer):
    dscr = serializers.SerializerMethodField()
    property_id = serializers.IntegerField(
        source="loan_request.property.id", read_only=True
    )
    property_name = serializers.CharField(
        source="loan_request.property.property_name", read_only=True
    )
    lender_email = serializers.EmailField(source="lender.email", read_only=True)
    lender_phone = serializers.CharField(source="lender.phone", read_only=True)
    lender_company = serializers.CharField(
        source="lender.company_name", read_only=True
    )
    lender_position = serializers.CharField(source="lender.position", read_only=True)
    lender_photo = serializers.SerializerMethodField()

    class Meta:
        model = LoanQuote
        fields = [
            "id",
            "loan_request",
            "property_id",
            "property_name",
            "lender",
            "lender_name",
            "lender_email",
            "lender_phone",
            "lender_company",
            "lender_position",
            "lender_photo",
            "guarantor",
            "status",
            "expires_at",
            "submitted_at",
            "updated_at",
            "loan_amount",
            "initial_funding",
            "future_funding",
            "sponsor_equity",
            "max_as_is_ltv",
            "max_ltc",
            "max_as_stabilized_ltv",
            "min_as_is_dy",
            "min_stabilized_dy",
            "term",
            "interest_rate",
            "amortization",
            "prepayment",
            "origination_fee",
            "capex_reserve",
            "ff_and_e_reserve",
            "interest_carry_reserve",
            "extension_conditions",
            "collateral",
            "recourse",
            "dscr",
        ]
        read_only_fields = [
            "id",
            "loan_request",
            "lender",
            "submitted_at",
            "updated_at",
            "dscr",
        ]

    def get_dscr(self, obj):
        return _compute_dscr(obj)

    def get_lender_photo(self, obj):
        request = self.context.get("request")
        if obj.lender.profile_photo and request:
            return request.build_absolute_uri(obj.lender.profile_photo.url)
        return None


class LoanQuoteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanQuote
        fields = [
            "lender_name",
            "guarantor",
            "expires_at",
            "loan_amount",
            "initial_funding",
            "future_funding",
            "sponsor_equity",
            "max_as_is_ltv",
            "max_ltc",
            "max_as_stabilized_ltv",
            "min_as_is_dy",
            "min_stabilized_dy",
            "term",
            "interest_rate",
            "amortization",
            "prepayment",
            "origination_fee",
            "capex_reserve",
            "ff_and_e_reserve",
            "interest_carry_reserve",
            "extension_conditions",
            "collateral",
            "recourse",
        ]

    def validate(self, data):
        if self.instance and self.instance.status != LoanQuote.STATUS_SUBMITTED:
            raise serializers.ValidationError(
                "Quote can only be updated while status is Submitted."
            )
        if "expires_at" in data and data["expires_at"] <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return data
