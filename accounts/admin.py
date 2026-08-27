from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from django.utils.translation import gettext_lazy as _

from accounts.models import (
    CustomUser,
    RoleModel,
    MediaFile,
    OTP,
    PasswordResetSession,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    list_display = [
        "email",
        "first_name",
        "last_name",
        "company_name",
        "display_active_role",
        "display_is_verified",
        "display_is_active",
        "date_joined",
    ]
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "company_name",
    ]
    list_filter = [
        "is_verified",
        "is_active",
        "active_role",
        "roles",
        "date_joined",
    ]
    ordering = ["-date_joined"]
    actions = ["action_verify_users", "action_activate_users"]

    fieldsets = (
        (
            _("Authentication"),
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            _("Personal Profile"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "profile_photo",
                )
            },
        ),
        (
            _("Roles & Context"),
            {
                "fields": (
                    "roles",
                    "active_role",
                )
            },
        ),
        (
            _("Company Information"),
            {
                "fields": (
                    "company_name",
                    "position",
                    "street_address",
                    "city",
                    "state",
                    "zip_code",
                )
            },
        ),
        (
            _("Permissions & Verification"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important Dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    @display(
        description=_("Active Role"),
        label={
            "Sponsor": "info",
            "Lender": "success",
        },
    )
    def display_active_role(self, obj):
        return obj.active_role or "—"

    @display(
        description=_("Verified"),
        boolean=True,
    )
    def display_is_verified(self, obj):
        return obj.is_verified

    @display(
        description=_("Active Status"),
        boolean=True,
    )
    def display_is_active(self, obj):
        return obj.is_active

    @action(description=_("Verify selected users"))
    def action_verify_users(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} user(s) successfully marked as verified.")

    @action(description=_("Activate selected users"))
    def action_activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} user(s) successfully activated.")


@admin.register(RoleModel)
class RoleAdmin(ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(MediaFile)
class MediaFileAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "display_role",
        "file",
        "uploaded_at",
    ]
    list_filter = ["role", "uploaded_at"]
    search_fields = ["user__email", "file"]
    readonly_fields = ["uploaded_at"]
    ordering = ["-uploaded_at"]

    @display(description=_("Role"), label=True)
    def display_role(self, obj):
        return obj.role.name if obj.role else "—"


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = [
        "id",
        "email",
        "otp_code",
        "display_otp_type",
        "display_is_used",
        "created_at",
        "expires_at",
    ]
    list_filter = ["otp_type", "is_used", "created_at"]
    search_fields = ["email", "otp_code"]
    readonly_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]

    @display(
        description=_("Type"),
        label={
            "SIGNUP": "info",
            "PASSWORD_RESET": "warning",
        },
    )
    def display_otp_type(self, obj):
        return obj.otp_type

    @display(description=_("Used"), boolean=True)
    def display_is_used(self, obj):
        return obj.is_used


@admin.register(PasswordResetSession)
class PasswordResetSessionAdmin(ModelAdmin):
    list_display = [
        "id",
        "email",
        "display_otp_verified",
        "created_at",
        "expires_at",
    ]
    search_fields = ["email"]
    readonly_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]

    @display(description=_("OTP Verified"), boolean=True)
    def display_otp_verified(self, obj):
        return obj.otp_verified
