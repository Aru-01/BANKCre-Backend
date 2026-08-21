from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from accounts.models import OTP


def send_otp_email(email, otp_code, otp_type):

    subjects = {
        "signup": "Verify Your BANKCre Email",
        "forgot_password": "Reset Your BANKCre Password",
    }

    template_names = {
        "signup": "emails/signup_otp.html",
        "forgot_password": "emails/forgot_password_otp.html",
    }

    subject = subjects[otp_type]

    html_content = render_to_string(
        template_names[otp_type],
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

    email_message = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.attach_alternative(
        html_content,
        "text/html",
    )

    email_message.send()


def create_otp(email, otp_type):

    last_otp = OTP.objects.filter(
        email=email,
        otp_type=otp_type,
    ).order_by('-created_at').first()

    if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 30:
        raise ValueError("Please wait 30 seconds before requesting a new OTP.")

    OTP.objects.filter(
        email=email,
        otp_type=otp_type,
        is_used=False,
    ).update(is_used=True)

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

        return False, "OTP has expired."

    otp.is_used = True

    otp.save(update_fields=["is_used"])

    return True, otp
