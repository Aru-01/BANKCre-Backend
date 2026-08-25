from django.contrib import admin
from unfold.admin import ModelAdmin
from memorandums.models import Memorandum, MemorandumSection


class MemorandumSectionInline(admin.TabularInline):
    model = MemorandumSection
    extra = 0
    readonly_fields = ["section_key", "section_type", "order", "updated_at"]
    fields = [
        "section_key",
        "section_type",
        "content",
        "table_data",
        "image",
        "order",
        "updated_at",
    ]
    ordering = ["order"]


@admin.register(Memorandum)
class MemorandumAdmin(ModelAdmin):
    list_display = ["title", "property", "sponsor", "status", "mode", "created_at"]
    list_filter = ["status", "mode"]
    search_fields = ["title", "property__property_name", "sponsor__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MemorandumSectionInline]
    ordering = ["-created_at"]


@admin.register(MemorandumSection)
class MemorandumSectionAdmin(ModelAdmin):
    list_display = ["memorandum", "section_key", "section_type", "order", "updated_at"]
    list_filter = ["section_type", "section_key"]
    search_fields = ["memorandum__title"]
    readonly_fields = ["updated_at"]
    ordering = ["memorandum", "order"]
