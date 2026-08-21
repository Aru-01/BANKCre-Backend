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
        },
    )

    message = f"Your BANKCre OTP is {otp_code}. " "It will expire in 10 minutes."

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
