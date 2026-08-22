from django.contrib import admin
from .models import (
    Property, PropertyFile, PropertyFileChunk,
    PropertyChatSession, PropertyChatMessage,
)


# ─────────────────────────────────────────────
# Inlines
# ─────────────────────────────────────────────

class PropertyFileInline(admin.TabularInline):
    model           = PropertyFile
    extra           = 0
    readonly_fields = ['category', 'file_name', 'file_type', 'image_source',
                       'uploaded_by', 'uploaded_by_role', 'uploaded_at']
    fields          = ['file', 'category', 'file_name', 'file_type',
                       'image_source', 'uploaded_by', 'uploaded_by_role', 'uploaded_at']


class PropertyFileChunkInline(admin.TabularInline):
    model           = PropertyFileChunk
    extra           = 0
    readonly_fields = ['chunk_index', 'chunk_text']
    fields          = ['chunk_index', 'chunk_text']
    exclude         = ['embedding']       # embeddings are large — hide from admin
    can_delete      = False
    max_num         = 0                   # read-only; prevent manual additions


class PropertyChatMessageInline(admin.TabularInline):
    model           = PropertyChatMessage
    extra           = 0
    readonly_fields = ['role', 'content', 'created_at']
    fields          = ['role', 'content', 'created_at']
    can_delete      = False
    ordering        = ['created_at']


# ─────────────────────────────────────────────
# ModelAdmin registrations
# ─────────────────────────────────────────────

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display        = ['id', 'property_name', 'property_type', 'sponsor', 'sponsor_role', 'created_at']
    list_filter         = ['property_type', 'sponsor_role']
    search_fields       = ['property_name', 'property_address', 'sponsor__email']
    readonly_fields     = ['created_at', 'updated_at']
    inlines             = [PropertyFileInline]
    list_select_related = ['sponsor', 'sponsor_role']


@admin.register(PropertyFile)
class PropertyFileAdmin(admin.ModelAdmin):
    list_display        = ['id', 'property', 'category', 'file_name', 'file_type',
                           'image_source', 'uploaded_by', 'uploaded_by_role', 'uploaded_at']
    list_filter         = ['category', 'file_type', 'image_source', 'uploaded_by_role']
    search_fields       = ['property__property_name', 'file_name', 'uploaded_by__email']
    readonly_fields     = ['uploaded_at']
    inlines             = [PropertyFileChunkInline]
    list_select_related = ['property', 'uploaded_by', 'uploaded_by_role']


@admin.register(PropertyFileChunk)
class PropertyFileChunkAdmin(admin.ModelAdmin):
    list_display        = ['id', 'file', 'chunk_index']
    search_fields       = ['file__file_name', 'file__property__property_name']
    readonly_fields     = ['file', 'chunk_index', 'chunk_text']
    exclude             = ['embedding']
    list_select_related = ['file__property']

    def has_add_permission(self, request):
        return False    # auto-generated; block manual creation


@admin.register(PropertyChatSession)
class PropertyChatSessionAdmin(admin.ModelAdmin):
    list_display        = ['id', 'property', 'user', 'title', 'updated_at']
    search_fields       = ['property__property_name', 'user__email', 'title']
    readonly_fields     = ['created_at', 'updated_at']
    inlines             = [PropertyChatMessageInline]
    list_select_related = ['property', 'user']


@admin.register(PropertyChatMessage)
class PropertyChatMessageAdmin(admin.ModelAdmin):
    list_display        = ['id', 'session', 'role', 'created_at']
    list_filter         = ['role']
    readonly_fields     = ['created_at']
    list_select_related = ['session__property']
