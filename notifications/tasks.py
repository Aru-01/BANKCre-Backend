import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_email_async_task(
    self,
    subject: str,
    body: str,
    from_email: str,
    recipient_list: list,
    html_content: str = None,
):
    """
    Asynchronous background Celery task to send transactional emails.
    Prevents HTTP request threads from blocking on external SMTP server delays.
    """
    try:
        sender = from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "BANCre <support@bancre.com>"
        )
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=sender,
            to=recipient_list,
        )
        if html_content:
            email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=False)
        logger.info("Async email sent successfully to: %s", recipient_list)
        return True
    except Exception as exc:
        logger.warning(
            "Retrying email to %s due to error: %s", recipient_list, exc
        )
        raise self.retry(exc=exc)
