from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from accounts.models import OTP


def send_otp_email(email, otp_code, otp_type):
    subjects = {
        "signup": "Verify Your BANCre Email",
        "forgot_password": "Reset Your BANCre Password",
    }

    template_names = {
        "signup": "emails/signup_otp.html",
        "forgot_password": "emails/forgot_password_otp.html",
    }

    subject = subjects.get(otp_type, "BANCre Verification Code")

    html_content = render_to_string(
        template_names.get(otp_type, "emails/signup_otp.html"),
        {
            "otp_code": otp_code,
            "email": email,
            "expiry_minutes": 10,
            "logo_url": settings.COMPANY_LOGO_URL,
        },
    )

    if otp_type == "signup":
        message = f"Welcome to BANCre! Your email verification code is {otp_code}.\nIt will expire in 10 minutes.\n\nIf you didn't request this, you can safely ignore this email."
    else:
        message = f"You requested a password reset for your BANCre account.\nYour password reset code is {otp_code}.\nIt will expire in 10 minutes.\n\nNever share this code with anyone. If you didn't request a reset, your account is safe."

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "BANCre <support@bancre.com>")

    try:
        from notifications.tasks import send_email_async_task

        send_email_async_task.delay(
            subject=subject,
            body=message,
            from_email=from_email,
            recipient_list=[email],
            html_content=html_content,
        )
    except Exception:
        # Fallback to direct send if Celery worker is unreachable
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=True)


def create_otp(email, otp_type):
    # Prune expired OTPs globally to keep DB clean
    OTP.objects.filter(expires_at__lt=timezone.now()).delete()

    last_otp = (
        OTP.objects.filter(
            email=email,
            otp_type=otp_type,
        )
        .order_by("-created_at")
        .first()
    )

    if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 30:
        raise ValueError("Please wait 30 seconds before requesting a new OTP.")

    # Remove any existing pending OTPs for this email and type
    OTP.objects.filter(
        email=email,
        otp_type=otp_type,
    ).delete()

    otp_code = OTP.generate_otp()

    otp = OTP.objects.create(
        email=email,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=(timezone.now() + timedelta(minutes=10)),
    )

    send_otp_email(
        email,
        otp_code,
        otp_type,
    )

    return otp


def verify_otp(email, otp_code, otp_type):
    try:
        otp = OTP.objects.get(
            email=email,
            otp_code=otp_code,
            otp_type=otp_type,
            is_used=False,
        )
    except OTP.DoesNotExist:
        return False, "Invalid OTP."

    if not otp.is_valid():
        otp.delete()
        return False, "OTP has expired."

    # Successfully verified — clean up OTP rows for this email & action
    OTP.objects.filter(email=email, otp_type=otp_type).delete()

    return True, otp
