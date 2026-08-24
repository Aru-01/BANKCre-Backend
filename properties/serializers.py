from rest_framework import serializers
from properties.models import (
    Property,
    PropertyFile,
    PropertyChatSession,
    PropertyChatMessage,
)


# Property File (images + documents unified)
class PropertyFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.SerializerMethodField()
    uploaded_by_role_name = serializers.SerializerMethodField()

    class Meta:
        model = PropertyFile
        fields = [
            "id",
            "file_url",
            "category",
            "file_name",
            "file_type",
            "image_source",
            "uploaded_by_email",
            "uploaded_by_role_name",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_uploaded_by_email(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by else None

    def get_uploaded_by_role_name(self, obj):
        return obj.uploaded_by_role.name if obj.uploaded_by_role else None


# Property — full detail
class PropertySerializer(serializers.ModelSerializer):
    files = PropertyFileSerializer(many=True, read_only=True)
    sponsor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "latitude",
            "longitude",
            "property_name",
            "property_address",
            "property_type",
            "number_of_units",
            "rentable_area",
            "year_built",
            "year_renovated",
            "occupancy",
            "parking_spaces",
            "sponsor",
            "created_at",
            "updated_at",
            "files",
        ]
        read_only_fields = ["id", "sponsor", "created_at", "updated_at", "files"]

    def validate_occupancy(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Occupancy must be between 0.00 and 100.00."
            )
        return value


# Property — lightweight list
class PropertyListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for list views — no full file list, just one
    thumbnail URL (first image attached to the property).
    """

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "property_name",
            "property_address",
            "property_type",
            "latitude",
            "longitude",
            "thumbnail_url",
            "created_at",
            "updated_at",
        ]

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        image = next(
            (f for f in obj.files.all() if f.category == PropertyFile.CATEGORY_IMAGE),
            None,
        )
        if image and request:
            return request.build_absolute_uri(image.file.url)
        return None


# Property — map markers (minimal)
class PropertyMapSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "property_name",
            "property_address",
            "property_type",
            "latitude",
            "longitude",
            "thumbnail_url",
        ]

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        image = next(
            (f for f in obj.files.all() if f.category == PropertyFile.CATEGORY_IMAGE),
            None,
        )
        if image and request:
            return request.build_absolute_uri(image.file.url)
        return None


# Chat
class PropertyChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyChatMessage
        fields = ["id", "role", "content", "created_at"]


class PropertyChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyChatSession
        fields = ["id", "property", "title", "created_at", "updated_at"]
        read_only_fields = ["id", "property", "created_at", "updated_at"]


class PropertyChatInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    session_id = serializers.IntegerField(required=False, allow_null=True)


# Place (from Google Maps frontend)
class PlaceSerializer(serializers.Serializer):
    """
    Receives place data from the frontend (Google Maps selection).
    Returns validated data so the frontend can pre-fill the property
    creation form and POST to /properties/ separately.
    """

    place_id = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)
    photos = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
    )
    rating = serializers.FloatField(required=False, allow_null=True, default=None)
    types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    # Claude extracted fields
    property_type = serializers.CharField(required=False, allow_null=True, default=None)
    number_of_units = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )
    rentable_area = serializers.FloatField(
        required=False, allow_null=True, default=None
    )
    year_built = serializers.IntegerField(required=False, allow_null=True, default=None)
    occupancy_rate = serializers.FloatField(
        required=False, allow_null=True, default=None
    )
    year_renovated = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )
    parking_spaces = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )
