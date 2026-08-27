from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from django.utils.translation import gettext_lazy as _

from memorandums.models import Memorandum, MemorandumSection


class MemorandumSectionInline(TabularInline):
    model = MemorandumSection
    extra = 0
    readonly_fields = ["section_key", "section_type", "order", "updated_at"]
    fields = [
        "section_key",
        "section_type",
        "content",
        "order",
        "updated_at",
    ]
    ordering = ["order"]


@admin.register(Memorandum)
class MemorandumAdmin(ModelAdmin):
    list_display = [
        "id",
        "title",
        "property",
        "sponsor",
        "display_status",
        "display_mode",
        "created_at",
    ]
    list_filter = ["status", "mode", "created_at"]
    search_fields = ["title", "property__property_name", "sponsor__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MemorandumSectionInline]
    actions = ["action_publish_memorandums"]
    ordering = ["-created_at"]

    @display(
        description=_("Status"),
        label={
            "Generating": "warning",
            "Draft": "info",
            "Published": "success",
            "Failed": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(
        description=_("Mode"),
        label={
            "Editor": "info",
            "Preview": "success",
        },
    )
    def display_mode(self, obj):
        return obj.mode

    @action(description=_("Publish selected memorandums"))
    def action_publish_memorandums(self, request, queryset):
        count = queryset.update(status=Memorandum.STATUS_PUBLISHED, mode="Preview")
        self.message_user(request, f"{count} memorandum(s) successfully marked as Published.")


@admin.register(MemorandumSection)
class MemorandumSectionAdmin(ModelAdmin):
    list_display = [
        "id",
        "memorandum",
        "section_key",
        "display_section_type",
        "order",
        "updated_at",
    ]
    list_filter = ["section_type", "section_key", "updated_at"]
    search_fields = ["memorandum__title", "section_key"]
    readonly_fields = ["updated_at"]
    ordering = ["memorandum", "order"]

    @display(
        description=_("Section Type"),
        label={
            "text": "info",
            "table": "purple",
        },
    )
    def display_section_type(self, obj):
        return obj.section_type
