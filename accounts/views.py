from datetime import timedelta
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import CustomUser, MediaFile, PasswordResetSession
from accounts import serializers as sz
from accounts.services import AuthService, PasswordService
from accounts.utils import create_otp, verify_otp


# Reusable Response Schemas
def get_success_schema(description="Success"):
    return openapi.Response(
        description,
        openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING),
                "data": openapi.Schema(type=openapi.TYPE_OBJECT),
            },
        ),
    )


def get_error_schema(description="Error"):
    return openapi.Response(
        description,
        openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING),
                "errors": openapi.Schema(type=openapi.TYPE_OBJECT),
            },
        ),
    )


class SignupView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="User Signup",
        request_body=sz.SignupSerializer,
        tags=["Auth / Account"],
        responses={
            201: get_success_schema(
                "Account created successfully. Please verify your email."
            ),
            400: get_error_schema("Validation failed"),
        },
    )
    def post(self, request):
        serializer = sz.SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        if serializer.errors:
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        try:
            create_otp(user.email, "signup")
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Account created successfully. Please verify your email.",
                "data": {"email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


class VerifySignupOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Signup OTP",
        request_body=sz.VerifyOTPSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("Email verified successfully."),
            400: get_error_schema("Invalid OTP"),
            404: get_error_schema("User not found"),
        },
    )
    def post(self, request):
        serializer = sz.VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]
        is_valid, result = verify_otp(email, otp_code, "signup")
        if not is_valid:
            return Response({"message": result}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return Response(
                {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response(
            {"message": "Email verified successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


class ResendSignupOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Resend Signup OTP",
        request_body=sz.ResendOTPSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("A new OTP has been sent."),
            400: get_error_schema("Validation failed"),
            404: get_error_schema("User not found or already verified"),
        },
    )
    def post(self, request):
        serializer = sz.ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        user = CustomUser.objects.filter(email=email, is_verified=False).first()

        if not user:
            return Response(
                {"message": "User not found or already verified."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            create_otp(email, "signup")
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "A new OTP has been sent."}, status=status.HTTP_200_OK
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="User Login",
        request_body=sz.LoginSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("Login successful"),
            400: get_error_schema("Validation failed"),
            401: get_error_schema("Invalid credentials"),
            403: get_error_schema("Email not verified"),
        },
    )
    def post(self, request):
        serializer = sz.LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        remember_me = serializer.validated_data["remember_me"]

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"message": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_verified:
            return Response(
                {"message": "Please verify your email before logging in."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        if not remember_me:
            refresh.set_exp(lifetime=timedelta(hours=1))

        return Response(
            {
                "message": "Login successful.",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": AuthService.get_user_data(user),
                },
            },
            status=status.HTTP_200_OK,
        )


class SwitchRoleView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Switch User Role",
        request_body=sz.SwitchRoleSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("Active role updated successfully."),
            400: get_error_schema("Validation failed"),
            403: get_error_schema("Access denied"),
        },
    )
    def patch(self, request):
        serializer = sz.SwitchRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = serializer.validated_data["role"]
        try:
            user = AuthService.switch_role(request.user, role)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            {
                "message": "Active role updated successfully.",
                "data": {
                    "active_role": user.active_role,
                    "roles": AuthService.get_user_roles(user),
                },
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Request Password Reset",
        request_body=sz.ForgotPasswordSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("OTP has been sent if account exists."),
            400: get_error_schema("Validation failed"),
        },
    )
    def post(self, request):
        serializer = sz.ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        user = CustomUser.objects.filter(email=email).first()
        if user:
            try:
                create_otp(email, "forgot_password")
            except ValueError as e:
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "If an account exists with this email, an OTP has been sent."},
            status=status.HTTP_200_OK,
        )


class VerifyForgotPasswordOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify Forgot Password OTP",
        request_body=sz.VerifyOTPSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("OTP verified"),
            400: get_error_schema("Invalid OTP"),
        },
    )
    def post(self, request):
        serializer = sz.VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]
        is_valid, result = verify_otp(email, otp_code, "forgot_password")
        if not is_valid:
            return Response({"message": result}, status=status.HTTP_400_BAD_REQUEST)

        PasswordService.create_reset_session(email)
        return Response(
            {"message": "OTP verified. You may now reset your password."},
            status=status.HTTP_200_OK,
        )


class ResendForgotPasswordOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Resend Forgot Password OTP",
        request_body=sz.ResendOTPSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("A new OTP has been sent if account exists."),
            400: get_error_schema("Validation failed"),
        },
    )
    def post(self, request):
        serializer = sz.ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        if CustomUser.objects.filter(email=email).exists():
            try:
                create_otp(email, "forgot_password")
            except ValueError as e:
                return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "If an account exists with this email, a new OTP has been sent."
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Reset Password",
        request_body=sz.ResetPasswordSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("Password reset successfully."),
            400: get_error_schema("Validation failed or session expired"),
            404: get_error_schema("User not found"),
        },
    )
    def post(self, request):
        serializer = sz.ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]
        reset_session = PasswordResetSession.objects.filter(
            email=email, otp_verified=True
        ).first()

        if not reset_session:
            return Response(
                {"message": "Please verify your OTP first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reset_session.is_valid():
            reset_session.delete()
            return Response(
                {"message": "Password reset session expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            PasswordService.reset_password(email, new_password)
        except CustomUser.DoesNotExist:
            return Response(
                {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        reset_session.delete()
        return Response(
            {"message": "Password reset successfully."}, status=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Change Password",
        request_body=sz.ChangePasswordSerializer,
        tags=["Auth / Account"],
        responses={
            200: get_success_schema("Password updated successfully."),
            400: get_error_schema("Validation failed"),
        },
    )
    def post(self, request):
        serializer = sz.ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]
        if not user.check_password(current_password):
            return Response(
                {"message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response(
            {"message": "Password updated successfully."}, status=status.HTTP_200_OK
        )


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Refresh JWT Token",
        tags=["Auth / Account"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh_token"],
            properties={"refresh_token": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={
            200: get_success_schema("Token refreshed successfully."),
            400: get_error_schema("refresh_token is required."),
            401: get_error_schema("Invalid or expired token."),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"message": "refresh_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response(
                {
                    "message": "Token refreshed successfully.",
                    "data": {"access": str(refresh.access_token)},
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"message": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Logout User",
        tags=["Auth / Account"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh_token"],
            properties={"refresh_token": openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={
            200: get_success_schema("Successfully logged out."),
            400: get_error_schema("Invalid token"),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"message": "refresh_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"message": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Successfully logged out."}, status=status.HTTP_200_OK
        )


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return sz.UpdateProfileSerializer
        return sz.UserProfileSerializer

    @swagger_auto_schema(
        operation_summary="Get User Profile",
        tags=["Auth / Account"],
        responses={200: sz.UserProfileSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update User Profile",
        tags=["Auth / Account"],
        request_body=sz.UpdateProfileSerializer,
        responses={200: sz.UserProfileSerializer},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Full Update User Profile",
        request_body=sz.UpdateProfileSerializer,
        tags=["Auth / Account"],
        responses={200: sz.UserProfileSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class MediaFileViewSet(ModelViewSet):
    serializer_class = sz.MediaFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return MediaFile.objects.filter(user=self.request.user).select_related("role")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
