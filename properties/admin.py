from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from properties.models import (
    Property,
    PropertyFile,
    PropertyFileChunk,
    PropertyChatSession,
    PropertyChatMessage,
)


class PropertyFileInline(TabularInline):
    model = PropertyFile
    extra = 0
    readonly_fields = [
        "category",
        "file_name",
        "file_type",
        "image_source",
        "uploaded_by",
        "uploaded_at",
    ]
    fields = [
        "file",
        "category",
        "file_name",
        "file_type",
        "image_source",
        "uploaded_by",
        "uploaded_at",
    ]


class PropertyFileChunkInline(TabularInline):
    model = PropertyFileChunk
    extra = 0
    readonly_fields = ["chunk_index", "chunk_text"]
    fields = ["chunk_index", "chunk_text"]
    exclude = ["embedding"]
    can_delete = False
    max_num = 0


class PropertyChatMessageInline(TabularInline):
    model = PropertyChatMessage
    extra = 0
    readonly_fields = ["role", "content", "created_at"]
    fields = ["role", "content", "created_at"]
    can_delete = False
    ordering = ["created_at"]


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = [
        "id",
        "property_name",
        "display_property_type",
        "sponsor",
        "display_occupancy",
        "year_built",
        "rentable_area",
        "created_at",
    ]
    list_filter = ["property_type", "year_built", "created_at"]
    search_fields = ["property_name", "property_address", "sponsor__email", "sponsor__first_name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PropertyFileInline]
    list_select_related = ["sponsor", "sponsor_role"]
    ordering = ["-created_at"]

    @display(
        description=_("Asset Type"),
        label={
            "multifamily": "info",
            "retail": "success",
            "industrial": "warning",
            "office": "purple",
            "other": "neutral",
        },
    )
    def display_property_type(self, obj):
        return obj.property_type or "other"

    @display(description=_("Occupancy"))
    def display_occupancy(self, obj):
        if obj.occupancy is not None:
            return f"{obj.occupancy}%"
        return "—"


@admin.register(PropertyFile)
class PropertyFileAdmin(ModelAdmin):
    list_display = [
        "id",
        "property",
        "display_category",
        "file_name",
        "file_type",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = ["category", "file_type", "image_source", "uploaded_at"]
    search_fields = ["property__property_name", "file_name", "uploaded_by__email"]
    readonly_fields = ["uploaded_at"]
    inlines = [PropertyFileChunkInline]
    list_select_related = ["property", "uploaded_by"]
    ordering = ["-uploaded_at"]

    @display(
        description=_("Category"),
        label={
            "image": "success",
            "document": "info",
            "other": "neutral",
        },
    )
    def display_category(self, obj):
        return obj.category


@admin.register(PropertyFileChunk)
class PropertyFileChunkAdmin(ModelAdmin):
    list_display = ["id", "file", "chunk_index"]
    search_fields = ["file__file_name", "file__property__property_name"]
    readonly_fields = ["file", "chunk_index", "chunk_text"]
    exclude = ["embedding"]
    list_select_related = ["file__property"]

    def has_add_permission(self, request):
        return False


@admin.register(PropertyChatSession)
class PropertyChatSessionAdmin(ModelAdmin):
    list_display = ["id", "property", "user", "title", "updated_at"]
    search_fields = ["property__property_name", "user__email", "title"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PropertyChatMessageInline]
    list_select_related = ["property", "user"]


@admin.register(PropertyChatMessage)
class PropertyChatMessageAdmin(ModelAdmin):
    list_display = ["id", "session", "display_role", "created_at"]
    list_filter = ["role", "created_at"]
    readonly_fields = ["created_at"]
    list_select_related = ["session__property"]

    @display(
        description=_("Role"),
        label={
            "user": "info",
            "assistant": "success",
            "system": "warning",
        },
    )
    def display_role(self, obj):
        return obj.role
