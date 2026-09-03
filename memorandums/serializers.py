import re
from rest_framework import serializers
from memorandums.models import Memorandum, MemorandumSection
from memorandums.ai_engine.extractors import SECTION_LABELS


def parse_content_to_table(content: str, section_key: str = "") -> dict:
    """
    Intelligently converts text/markdown content into tabular data
    {"columns": [...], "rows": [[...], ...]} so that the frontend can
    render every section as a table seamlessly.
    """
    if not content:
        return {"columns": ["Item", "Details"], "rows": []}

    # 1. Key-Value pairs (e.g. property_information)
    if section_key == "property_information" or (
        content.count(": ") >= 3 and "#" not in content
    ):
        rows = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                parts = line.split(":", 1)
                rows.append([parts[0].strip(), parts[1].strip()])
            else:
                rows.append(["Info", line])
        return {"columns": ["Attribute", "Value"], "rows": rows}

    # 2. Markdown Headings (## or ###)
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(content))
    if len(matches) >= 2:
        rows = []
        for i in range(len(matches)):
            start_pos = matches[i].end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            title = matches[i].group(2).strip()
            body = content[start_pos:end_pos].strip()
            body = re.sub(r"^-{3,}$", "", body, flags=re.MULTILINE).strip()
            if body:
                rows.append([title, body])
        if rows:
            return {"columns": ["Topic", "Details"], "rows": rows}

    # 3. Bullet points (- or *)
    bullets = re.findall(r"^\s*[-*]\s+(.+)$", content, re.MULTILINE)
    if bullets:
        rows = []
        for b in bullets:
            b = b.strip()
            if "**" in b and ":" in b:
                m = re.match(r"^\*{0,2}(.*?)\*{0,2}:\s*(.*)$", b)
                if m:
                    rows.append(
                        [m.group(1).replace("*", "").strip(), m.group(2).strip()]
                    )
                else:
                    rows.append(["Highlight", b.replace("*", "")])
            else:
                rows.append(["Highlight", b.replace("*", "")])
        return {"columns": ["Feature", "Description"], "rows": rows}

    # 4. Fallback: split by paragraphs
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    rows = []
    for i, p in enumerate(paragraphs, 1):
        clean_p = re.sub(r"^[#-]+\s*", "", p).strip()
        rows.append([f"Section {i}", clean_p])
    return {"columns": ["Item", "Details"], "rows": rows}


class MemorandumSectionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    is_regeneratable = serializers.SerializerMethodField()
    image = serializers.ImageField(use_url=True, required=False, allow_null=True)
    table_data = serializers.SerializerMethodField()
    section_type = serializers.SerializerMethodField()

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

    def get_section_type(self, obj):
        # Always return 'table' format to satisfy frontend tabular rendering requirement
        return "table"

    def get_table_data(self, obj):
        if (
            obj.table_data
            and isinstance(obj.table_data, dict)
            and obj.table_data.get("columns")
        ):
            return obj.table_data
        return parse_content_to_table(obj.content, obj.section_key)


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
    property_address = serializers.CharField(
        source="property.property_address", read_only=True
    )
    property_type = serializers.CharField(
        source="property.property_type", read_only=True
    )
    occupancy = serializers.DecimalField(
        source="property.occupancy", max_digits=5, decimal_places=2, read_only=True
    )
    year_built = serializers.IntegerField(
        source="property.year_built", read_only=True
    )
    rentable_area = serializers.DecimalField(
        source="property.rentable_area", max_digits=12, decimal_places=2, read_only=True
    )
    number_of_units = serializers.IntegerField(
        source="property.number_of_units", read_only=True
    )
    property_images = serializers.SerializerMethodField()
    sections = MemorandumSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Memorandum
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
            "property_images",
            "title",
            "status",
            "mode",
            "sections",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_property_images(self, obj):
        request = self.context.get("request")
        # Utilize in-memory prefetched cache to avoid duplicate SQL queries
        images = [f for f in obj.property.files.all() if f.category == "image"]
        urls = []
        for img in images:
            if img.file:
                url = request.build_absolute_uri(img.file.url) if request else img.file.url
                urls.append(url)
        return urls


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
