import random
import string
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from accounts.managers import CustomUserManager


class Role(models.TextChoices):
    LENDER = "Lender", "Lender"
    SPONSOR = "Sponsor", "Sponsor"


class RoleModel(models.Model):
    name = models.CharField(
        max_length=20,
        choices=Role.choices,
        unique=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"


class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(
        unique=True,
        db_index=True,
    )
    phone = models.CharField(max_length=20)
    is_verified = models.BooleanField(default=False)
    active_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SPONSOR,
    )
    roles = models.ManyToManyField(
        RoleModel,
        related_name="users",
        blank=True,
    )
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
    )
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    position = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )
    street_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    zip_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(
        default=timezone.now,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def has_role(self, role):
        if self.is_superuser:
            return True
        if getattr(self, "active_role", None) == role:
            return True
        cache_attr = f"_has_role_{role}"
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, self.roles.filter(name=role).exists())
        return getattr(self, cache_attr)

    def get_roles(self):
        return list(self.roles.values_list("name", flat=True))

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class MediaFile(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="media_files",
    )
    role = models.ForeignKey(
        RoleModel,
        on_delete=models.CASCADE,
        related_name="media_files",
    )

    file = models.FileField(upload_to="media_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - " f"{self.role.name} - " f"{self.file.name}"

    class Meta:
        verbose_name = "Media File"
        verbose_name_plural = "Media Files"
        ordering = ["-uploaded_at"]

        indexes = [
            models.Index(fields=["user", "role"]),
        ]


class OTP(models.Model):

    class OTPType(models.TextChoices):
        SIGNUP = "signup", "Signup"
        FORGOT_PASSWORD = (
            "forgot_password",
            "Forgot Password",
        )

    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(
        max_length=20,
        choices=OTPType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    @staticmethod
    def generate_otp():
        return "".join(
            random.choices(
                string.digits,
                k=6,
            )
        )

    def __str__(self):
        return f"{self.email} - {self.otp_type}"

    class Meta:
        ordering = ["-created_at"]


class PasswordResetSession(models.Model):

    email = models.EmailField(db_index=True)
    otp_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return self.otp_verified and timezone.now() < self.expires_at

    class Meta:
        ordering = ["-created_at"]


# media file tokhon add hobe jokhon user kono property or lender kono property purchase a jabe  etc etc
