import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from notifications.models import Notification, NotificationPreference

logger = logging.getLogger(__name__)
User = get_user_model()


def send_templated_email(
    subject: str,
    template_name: str,
    context: dict,
    recipient_email: str,
    plain_fallback: str = "",
) -> None:
    """Send an HTML-templated email with a plaintext alternative safely."""
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "support@bancre.com")
        html_content = render_to_string(template_name, context)
        text_content = plain_fallback or f"{subject}\n\nPlease view this email in an HTML-compatible email client."

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=True)
    except Exception as e:
        logger.error(
            "Failed to send templated email [%s] to %s: %s",
            template_name,
            recipient_email,
            str(e),
            exc_info=True,
        )


def is_quote_email_enabled(user) -> bool:
    """Check if the user has enabled quote-related email alerts."""
    try:
        pref, _ = NotificationPreference.objects.get_or_create(user=user)
        return pref.quote_emails_enabled
    except Exception:
        return True


def notify_sponsor_new_quote(loan_request, quote) -> None:
    """Notify sponsor when a new quote is submitted for their loan request."""
    sponsor = loan_request.sponsor
    property_name = loan_request.property.property_name
    lender_name = quote.lender_name or f"{quote.lender.first_name} {quote.lender.last_name}".strip() or "A lender"

    # In-app notification
    Notification.objects.create(
        recipient=sponsor,
        notification_type=Notification.QUOTE_SUBMITTED,
        title="New Quote Received",
        message=f"A lender ({lender_name}) has submitted a loan quote for {property_name}.",
        loan_request_id=loan_request.id,
        quote_id=quote.id,
    )

    # Templated Email notification
    if is_quote_email_enabled(sponsor):
        subject = f"New Quote Received — {property_name}"
        context = {
            "sponsor_name": sponsor.first_name or "Sponsor",
            "lender_name": lender_name,
            "property_name": property_name,
            "loan_amount": f"{quote.loan_amount:,.2f}",
            "interest_rate": quote.interest_rate,
            "term": quote.term,
            "initial_funding": f"{quote.initial_funding:,.2f}",
            "dscr": getattr(quote, "dscr", None),
        }
        plain_fallback = (
            f"Hello {sponsor.first_name},\n\n"
            f"A new quote has been submitted by {lender_name} for your loan request on {property_name}.\n\n"
            f"Loan Amount: ${quote.loan_amount:,.2f}\n"
            f"Interest Rate: {quote.interest_rate}%\n"
            f"Term: {quote.term} months\n\n"
            f"Log in to BANCre to review and compare quotes.\n\nBANCre Team"
        )
        send_templated_email(
            subject=subject,
            template_name="emails/new_quote_received.html",
            context=context,
            recipient_email=sponsor.email,
            plain_fallback=plain_fallback,
        )


def notify_lender_quote_accepted(quote) -> None:
    """Notify lender that their quote was accepted."""
    lender = quote.lender
    property_name = quote.loan_request.property.property_name
    lender_name = quote.lender_name or f"{lender.first_name} {lender.last_name}".strip() or "Lender"

    # In-app notification
    Notification.objects.create(
        recipient=lender,
        notification_type=Notification.QUOTE_ACCEPTED,
        title="Your Quote Was Accepted",
        message=f"Congratulations! Your quote for {property_name} has been accepted by the sponsor.",
        loan_request_id=quote.loan_request.id,
        quote_id=quote.id,
    )

    # Templated Email notification
    if is_quote_email_enabled(lender):
        subject = f"Your Quote Has Been Accepted — {property_name}"
        context = {
            "lender_name": lender_name,
            "property_name": property_name,
            "loan_amount": f"{quote.loan_amount:,.2f}",
            "interest_rate": quote.interest_rate,
            "term": quote.term,
        }
        plain_fallback = (
            f"Hello {lender_name},\n\n"
            f"Congratulations! Your loan quote for {property_name} has been accepted by the sponsor.\n\n"
            f"Loan Amount: ${quote.loan_amount:,.2f}\n"
            f"Log in to view the full details and finalize the next steps.\n\nBANCre Team"
        )
        send_templated_email(
            subject=subject,
            template_name="emails/quote_accepted.html",
            context=context,
            recipient_email=lender.email,
            plain_fallback=plain_fallback,
        )


def notify_lender_quote_declined(quote) -> None:
    """Notify lender that their quote was declined."""
    lender = quote.lender
    property_name = quote.loan_request.property.property_name
    lender_name = quote.lender_name or f"{lender.first_name} {lender.last_name}".strip() or "Lender"

    # In-app notification
    Notification.objects.create(
        recipient=lender,
        notification_type=Notification.QUOTE_DECLINED,
        title="Your Quote Was Declined",
        message=f"Your quote for {property_name} has been declined by the sponsor.",
        loan_request_id=quote.loan_request.id,
        quote_id=quote.id,
    )

    # Templated Email notification
    if is_quote_email_enabled(lender):
        subject = f"Your Quote Has Been Declined — {property_name}"
        context = {
            "lender_name": lender_name,
            "property_name": property_name,
        }
        plain_fallback = (
            f"Hello {lender_name},\n\n"
            f"Your quote for the loan request on {property_name} has been declined.\n\n"
            f"Thank you for your participation.\n\nBANCre Team"
        )
        send_templated_email(
            subject=subject,
            template_name="emails/quote_declined.html",
            context=context,
            recipient_email=lender.email,
            plain_fallback=plain_fallback,
        )


def notify_lenders_new_loan_request(loan_request) -> None:
    """Broadcast notification to all active lenders when a new loan request is listed."""
    property_name = loan_request.property.property_name
    sponsor = loan_request.sponsor

    # Find active lenders excluding the sponsor
    lenders = (
        User.objects.filter(
            roles__name="Lender",
            is_active=True,
        )
        .exclude(id=sponsor.id)
        .distinct()
    )

    notifications = [
        Notification(
            recipient=lender,
            notification_type=Notification.LOAN_REQUEST_CREATED,
            title="New Loan Request Available",
            message=f"A new loan request has been listed for {property_name}. Requested amount: ${loan_request.requested_amount:,.2f}.",
            loan_request_id=loan_request.id,
        )
        for lender in lenders
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_lenders_loan_request_updated(loan_request) -> None:
    """Broadcast notification to all active lenders when a loan request is updated."""
    property_name = loan_request.property.property_name
    sponsor = loan_request.sponsor

    lenders = (
        User.objects.filter(
            roles__name="Lender",
            is_active=True,
        )
        .exclude(id=sponsor.id)
        .distinct()
    )

    notifications = [
        Notification(
            recipient=lender,
            notification_type=Notification.LOAN_REQUEST_UPDATED,
            title="Loan Request Updated",
            message=f"A loan request for {property_name} has been updated by the sponsor.",
            loan_request_id=loan_request.id,
        )
        for lender in lenders
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_sponsor_memorandum_ready(memorandum) -> None:
    """Notify sponsor when their offering memorandum is generated."""
    property_name = memorandum.property.property_name
    sponsor = memorandum.sponsor

    Notification.objects.create(
        recipient=sponsor,
        notification_type=Notification.MEMORANDUM_GENERATED,
        title="Memorandum Ready",
        message=f"Your offering memorandum for {property_name} has been successfully generated.",
        memorandum_id=memorandum.id,
    )

    # Templated Email
    subject = f"Offering Memorandum Ready — {property_name}"
    context = {
        "sponsor_name": sponsor.first_name or "Sponsor",
        "property_name": property_name,
        "memorandum_title": memorandum.title,
    }
    send_templated_email(
        subject=subject,
        template_name="emails/memorandum_ready.html",
        context=context,
        recipient_email=sponsor.email,
        plain_fallback=f"Your offering memorandum for {property_name} has been generated.",
    )
