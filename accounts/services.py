from datetime import timedelta
from django.utils import timezone
from accounts.models import (
    CustomUser,
    PasswordResetSession,
)


class AuthService:
    @staticmethod
    def get_user_roles(user):
        return list(user.roles.values_list("name", flat=True))

    @staticmethod
    def get_user_data(user):
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "roles": AuthService.get_user_roles(user),
            "active_role": user.active_role,
        }

    @staticmethod
    def switch_role(user, role):
        if not user.has_role(role):
            raise ValueError("You do not have access to this role.")

        user.active_role = role
        user.save(update_fields=["active_role"])
        return user


class PasswordService:
    @staticmethod
    def create_reset_session(email):
        PasswordResetSession.objects.filter(email=email).delete()
        return PasswordResetSession.objects.create(
            email=email,
            otp_verified=True,
            expires_at=(timezone.now() + timedelta(minutes=15)),
        )

    @staticmethod
    def reset_password(email, new_password):
        user = CustomUser.objects.get(email=email)
        user.set_password(new_password)
        user.save(update_fields=["password"])


class MediaFileService:
    @staticmethod
    def validate_role(user, role):
        if not user.has_role(role.name):
            raise ValueError("You do not have access to this role.")

