from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from accounts.models import CustomUser, MediaFile, Role, RoleModel


class UserProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "profile_photo",
            "company_name",
            "position",
            "street_address",
            "city",
            "state",
            "zip_code",
            "roles",
            "active_role",
        ]

        read_only_fields = [
            "id",
            "email",
            "roles",
            "active_role",
        ]

    def get_roles(self, obj):
        return list(obj.roles.values_list("name", flat=True))


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "phone",
            "profile_photo",
            "company_name",
            "position",
            "street_address",
            "city",
            "state",
            "zip_code",
        ]


class SignupSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "password",
            "confirm_password",
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        try:
            validate_password(data["password"])

        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(password=password, **validated_data)
        lender_role, _ = RoleModel.objects.get_or_create(name=Role.LENDER)
        sponsor_role, _ = RoleModel.objects.get_or_create(name=Role.SPONSOR)
        user.roles.set(
            [
                lender_role,
                sponsor_role,
            ]
        )
        user.active_role = Role.SPONSOR
        user.save(update_fields=["active_role"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(
        min_length=6,
        max_length=6,
    )


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SwitchRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )

        try:
            validate_password(data["new_password"])

        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return data


class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):

        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        try:
            validate_password(data["new_password"])

        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return data


class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = [
            "id",
            "role",
            "file",
            "uploaded_at",
        ]

        read_only_fields = [
            "id",
            "uploaded_at",
        ]

    def validate_role(self, role):
        user = self.context["request"].user
        if not user.roles.filter(pk=role.pk).exists():
            raise serializers.ValidationError("You do not have access to this role.")
        return role

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
