import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from notifications.models import NotificationPreference
from notifications.services import (
    notify_sponsor_new_quote,
    notify_lender_quote_accepted,
    notify_lender_quote_declined,
    notify_lenders_new_loan_request,
    notify_lenders_loan_request_updated,
    notify_sponsor_memorandum_ready,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# Auto-create user notification preference on user signup
@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        NotificationPreference.objects.get_or_create(user=instance)


# Pre-save signal for Memorandum to detect status change
@receiver(pre_save, sender="memorandums.Memorandum")
def capture_memorandum_pre_status(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        instance._pre_status = sender.objects.get(pk=instance.pk).status
    except sender.DoesNotExist:
        instance._pre_status = None


# Post-save signal for Memorandum
@receiver(post_save, sender="memorandums.Memorandum")
def on_memorandum_saved(sender, instance, created, **kwargs):
    # If newly transitioned to Draft from Generating
    previous_status = getattr(instance, "_pre_status", None)
    if previous_status == "Generating" and instance.status in ("Draft", "Published"):
        notify_sponsor_memorandum_ready(instance)


# Post-save signal for LoanRequest
@receiver(post_save, sender="loan.LoanRequest")
def on_loan_request_saved(sender, instance, created, **kwargs):
    try:
        if created:
            notify_lenders_new_loan_request(instance)
        elif instance.status == "Active":
            notify_lenders_loan_request_updated(instance)
    except Exception as e:
        logger.error("Error in on_loan_request_saved signal: %s", str(e), exc_info=True)


# Pre-save signal for LoanQuote to detect status changes
@receiver(pre_save, sender="loan.LoanQuote")
def capture_quote_pre_status(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        instance._pre_status = sender.objects.get(pk=instance.pk).status
    except sender.DoesNotExist:
        instance._pre_status = None


# Post-save signal for LoanQuote
@receiver(post_save, sender="loan.LoanQuote")
def on_loan_quote_saved(sender, instance, created, **kwargs):
    try:
        if created:
            notify_sponsor_new_quote(instance.loan_request, instance)
            return

        previous_status = getattr(instance, "_pre_status", None)
        current_status = instance.status

        if previous_status == current_status:
            return

        if current_status == "Accepted":
            notify_lender_quote_accepted(instance)
        elif current_status == "Declined":
            notify_lender_quote_declined(instance)
    except Exception as e:
        logger.error("Error in on_loan_quote_saved signal: %s", str(e), exc_info=True)
