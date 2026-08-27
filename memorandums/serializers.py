from rest_framework import serializers
from memorandums.models import Memorandum, MemorandumSection
from memorandums.ai_engine.extractors import SECTION_LABELS


class MemorandumSectionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    is_regeneratable = serializers.SerializerMethodField()
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = MemorandumSection
        fields = [
            "id",
            "section_key",
            "label",
            "section_type",
            "is_regeneratable",
            "content",
            "table_data",
            "image",
            "order",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "section_key",
            "label",
            "section_type",
            "is_regeneratable",
            "order",
            "updated_at",
        ]

    def get_label(self, obj):
        return SECTION_LABELS.get(obj.section_key, obj.section_key)

    def get_is_regeneratable(self, obj):
        return obj.is_regeneratable


class MemorandumListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(
        source="property.property_name", read_only=True
    )
    section_count = serializers.SerializerMethodField()

    class Meta:
        model = Memorandum
        fields = [
            "id",
            "property",
            "property_name",
            "title",
            "status",
            "mode",
            "section_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property_name",
            "section_count",
            "created_at",
            "updated_at",
        ]

    def get_section_count(self, obj):
        return obj.sections.count()


class MemorandumDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(
        source="property.property_name", read_only=True
    )
    sections = MemorandumSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Memorandum
        fields = [
            "id",
            "property",
            "property_name",
            "title",
            "status",
            "mode",
            "sections",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property",
            "property_name",
            "sections",
            "created_at",
            "updated_at",
        ]


class MemorandumUpdateSerializer(serializers.ModelSerializer):
    """For PATCH: title, mode, and status (e.g. Draft -> Published) are editable."""

    class Meta:
        model = Memorandum
        fields = ["title", "mode", "status"]

    def validate_status(self, value):
        if value not in [Memorandum.STATUS_DRAFT, Memorandum.STATUS_PUBLISHED]:
            raise serializers.ValidationError(
                f"Status can only be set to '{Memorandum.STATUS_DRAFT}' or '{Memorandum.STATUS_PUBLISHED}'."
            )
        return value


class GenerateMemorandumSerializer(serializers.Serializer):
    """Input serializer for POST /memorandums/generate/"""

    property_id = serializers.IntegerField()


class MemorandumSectionUpdateSerializer(serializers.ModelSerializer):
    """For manual content edit (text sections only)."""

    class Meta:
        model = MemorandumSection
        fields = ["content"]

    def validate(self, data):
        if (
            self.instance
            and self.instance.section_type == MemorandumSection.SECTION_TYPE_TABLE
        ):
            raise serializers.ValidationError(
                "Table sections cannot be manually edited. Use regenerate for text sections."
            )
        return data


class SectionImageSerializer(serializers.ModelSerializer):
    """For POST /sections/<id>/image/ — upload a section image."""

    class Meta:
        model = MemorandumSection
        fields = ["image"]


class RegenerateSectionSerializer(serializers.Serializer):
    """Input for POST /sections/<id>/regenerate/"""

    custom_instruction = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text='Optional: e.g. "Make it shorter" or "Emphasize transit access"',
    )
