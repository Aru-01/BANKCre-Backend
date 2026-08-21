from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
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
        "active_role",
        "is_verified",
        "is_active",
    ]

    search_fields = [
        "email",
        "first_name",
        "last_name",
    ]

    list_filter = [
        "is_verified",
        "is_active",
        "active_role",
        "roles",
    ]

    ordering = ["-date_joined"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
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
            "Roles",
            {
                "fields": (
                    "roles",
                    "active_role",
                )
            },
        ),
        (
            "Company Information",
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
            "Permissions",
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
            "Important Dates",
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


@admin.register(RoleModel)
class RoleAdmin(ModelAdmin):

    list_display = [
        "name",
    ]

    search_fields = [
        "name",
    ]

    ordering = [
        "name",
    ]


@admin.register(MediaFile)
class MediaFileAdmin(ModelAdmin):

    list_display = [
        "id",
        "user",
        "role",
        "file",
        "uploaded_at",
    ]

    list_filter = [
        "role",
    ]

    search_fields = [
        "user__email",
    ]

    readonly_fields = [
        "uploaded_at",
    ]

    ordering = ["-uploaded_at"]


@admin.register(OTP)
class OTPAdmin(ModelAdmin):

    list_display = [
        "email",
        "otp_type",
        "is_used",
        "created_at",
        "expires_at",
    ]

    list_filter = [
        "otp_type",
        "is_used",
    ]

    search_fields = [
        "email",
    ]

    readonly_fields = [
        "created_at",
        "expires_at",
    ]


@admin.register(PasswordResetSession)
class PasswordResetSessionAdmin(ModelAdmin):

    list_display = [
        "email",
        "otp_verified",
        "created_at",
        "expires_at",
    ]

    search_fields = [
        "email",
    ]

    readonly_fields = [
        "created_at",
        "expires_at",
    ]
