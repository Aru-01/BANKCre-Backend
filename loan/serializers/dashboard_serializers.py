from rest_framework import serializers
from loan.models import LoanRequest, LoanQuote
from loan.serializers.quote_serializers import _compute_dscr


class LenderDashboardRequestSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source="property.id", read_only=True)
    property_name = serializers.CharField(
        source="property.property_name", read_only=True
    )
    property_address = serializers.CharField(
        source="property.property_address", read_only=True
    )
    property_type = serializers.CharField(
        source="property.property_type", read_only=True
    )
    occupancy = serializers.DecimalField(
        source="property.occupancy", max_digits=5, decimal_places=2, read_only=True
    )
    year_built = serializers.IntegerField(source="property.year_built", read_only=True)
    property_image_url = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "property_id",
            "property_name",
            "property_address",
            "property_type",
            "occupancy",
            "year_built",
            "property_image_url",
            "requested_amount",
            "loan_term",
            "ltv",
            "created_at",
        ]

    def get_property_image_url(self, obj):
        request = self.context.get("request")
        image_file = obj.property.files.filter(category="image").first()
        if image_file and image_file.file and request:
            return request.build_absolute_uri(image_file.file.url)
        return None


class SponsorQuoteCardSerializer(serializers.ModelSerializer):
    dscr = serializers.SerializerMethodField()
    property_id = serializers.IntegerField(
        source="loan_request.property.id", read_only=True
    )
    property_name = serializers.CharField(
        source="loan_request.property.property_name", read_only=True
    )

    class Meta:
        model = LoanQuote
        fields = [
            "id",
            "loan_request",
            "property_id",
            "property_name",
            "lender_name",
            "loan_amount",
            "max_as_is_ltv",
            "interest_rate",
            "term",
            "origination_fee",
            "dscr",
            "expires_at",
            "status",
            "submitted_at",
        ]

    def get_dscr(self, obj):
        return _compute_dscr(obj)
