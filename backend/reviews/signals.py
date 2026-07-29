import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Review
from .services.moderation_service import OpenAIModerationService

logger = logging.getLogger(__name__)

moderation_service = OpenAIModerationService()


def _needs_moderation(instance: Review) -> bool:
    """True for new reviews, and for any save that changes the content.

    The API no longer exposes update, but re-moderating on content change
    keeps the guarantee at the model layer, which the admin and any future
    code path also have to go through.
    """
    if instance.pk is None:
        return True

    previous_content = (
        Review.objects.filter(pk=instance.pk).values_list("content", flat=True).first()
    )
    return previous_content is not None and previous_content != instance.content


@receiver(pre_save, sender=Review)
def auto_moderate(sender, instance: Review, **kwargs):
    """Moderate review content before it is saved."""
    if not _needs_moderation(instance):
        return

    try:
        moderation_result = moderation_service.moderate(instance.content)

        instance.risk_category = moderation_result.get("risk_category", "appropriate")
        instance.risk_score = moderation_result.get("risk_score", 0.0)
        instance.status = moderation_result.get("status", "pending")
        instance.moderation_data_full = moderation_result.get("moderation_data_full", {})
        instance.moderated_at = timezone.now()

        logger.info(
            "Moderated review: status=%s category=%s risk_score=%.2f",
            instance.status,
            instance.risk_category,
            instance.risk_score,
        )

    except Exception as e:
        # Never record a failure as a clean verdict: hold the review instead.
        logger.error("Moderation failed, holding review as pending: %s", e)
        instance.status = "pending"
        instance.risk_category = "unknown"
        instance.risk_score = 0.0
        instance.moderation_data_full = {"error": str(e)}
        instance.moderated_at = timezone.now()
