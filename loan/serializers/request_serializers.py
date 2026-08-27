from decimal import Decimal
from rest_framework import serializers
from loan.models import LoanRequest


class LoanRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = ["property", "requested_amount", "loan_term", "ltv"]

    def validate_property(self, value):
        request = self.context.get("request")
        if request and value.sponsor_id != request.user.id:
            raise serializers.ValidationError("You do not own this property.")
        return value

    def validate_requested_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError(
                "Requested amount must be greater than zero."
            )
        return value

    def validate_loan_term(self, value):
        if value <= 0:
            raise serializers.ValidationError("Loan term must be a positive integer.")
        return value

    def validate_ltv(self, value):
        if value <= Decimal("0.00") or value > Decimal("100.00"):
            raise serializers.ValidationError(
                "LTV percentage must be between 0 and 100."
            )
        return value


class LoanRequestListSerializer(serializers.ModelSerializer):
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
    quotes_count = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "property",
            "property_name",
            "property_address",
            "property_type",
            "occupancy",
            "year_built",
            "property_image_url",
            "requested_amount",
            "loan_term",
            "ltv",
            "status",
            "quotes_count",
            "created_at",
        ]

    def get_property_image_url(self, obj):
        request = self.context.get("request")
        image_file = obj.property.files.filter(category="image").first()
        if image_file and image_file.file and request:
            return request.build_absolute_uri(image_file.file.url)
        return None

    def get_quotes_count(self, obj):
        if hasattr(obj, "quotes_count_annotated"):
            return obj.quotes_count_annotated
        return obj.quotes.count()


class LoanRequestDetailSerializer(serializers.ModelSerializer):
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
    rentable_area = serializers.DecimalField(
        source="property.rentable_area", max_digits=12, decimal_places=2, read_only=True
    )
    number_of_units = serializers.IntegerField(
        source="property.number_of_units", read_only=True
    )
    parking_spaces = serializers.IntegerField(
        source="property.parking_spaces", read_only=True
    )
    property_image_url = serializers.SerializerMethodField()
    memorandum_links = serializers.SerializerMethodField()
    document_links = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "property",
            "property_name",
            "property_address",
            "property_type",
            "occupancy",
            "year_built",
            "rentable_area",
            "number_of_units",
            "parking_spaces",
            "property_image_url",
            "requested_amount",
            "loan_term",
            "ltv",
            "status",
            "created_at",
            "updated_at",
            "memorandum_links",
            "document_links",
        ]

    def get_property_image_url(self, obj):
        request = self.context.get("request")
        image_file = obj.property.files.filter(category="image").first()
        if image_file and image_file.file and request:
            return request.build_absolute_uri(image_file.file.url)
        return None

    def get_memorandum_links(self, obj):
        request = self.context.get("request")
        # If the requester is the owning sponsor, show Draft and Published memorandums
        if request and request.user and request.user.id == obj.sponsor_id:
            memos = obj.property.memorandums.exclude(status="Failed").values(
                "id", "title", "status"
            )
        else:
            # For lenders, show Published memorandums
            memos = obj.property.memorandums.filter(status="Published").values(
                "id", "title", "status"
            )

        if not request:
            return list(memos)
        return [
            {
                "id": m["id"],
                "title": m["title"],
                "status": m["status"],
                "url": request.build_absolute_uri(f"/api/v1/memorandums/{m['id']}/"),
            }
            for m in memos
        ]

    def get_document_links(self, obj):
        request = self.context.get("request")
        docs = obj.property.files.filter(category="document")
        if not request:
            return []
        return [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "url": request.build_absolute_uri(doc.file.url),
            }
            for doc in docs
            if doc.file
        ]


class LoanRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = ["requested_amount", "loan_term", "ltv", "status"]

    def validate_status(self, value):
        instance = self.instance
        if instance and instance.status == LoanRequest.STATUS_CLOSED:
            raise serializers.ValidationError("Cannot update a closed loan request.")
        return value
