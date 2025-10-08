from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Review
from .services.moderation_service import OpenAIModerationService

moderation_service = OpenAIModerationService()


@receiver(pre_save, sender=Review)
def auto_moderate(sender, instance: Review, **kwargs):
    """
    Automatically moderate new reviews before they are saved.
    Only moderate when the review is new (no PK).
    """
    if instance.pk is None:
        if instance.pk is None:  # Only moderate new reviews
            print("New Review Submitted - Initiating Automatic Review")
            try:
                moderation_result = moderation_service.moderate(instance.content)

                instance.risk_category = moderation_result.get("risk_category", "appropriate")
                instance.confidence = moderation_result.get("confidence", 0.0)
                instance.status = moderation_result.get("status", "pending")
                instance.moderation_data_full = moderation_result.get("moderation_data_full", {})
                instance.moderated_at = timezone.now()

                print("Moderation Result Logging:")
                print(f"* Status: {instance.status}")
                print(f"* Risk Category: {instance.risk_category}")
                print(f"* Confidence: {instance.confidence:.2f}")

            except Exception as e:
                print(f"Moderation failed: {e}")
                instance.status = "pending"
                instance.risk_category = "appropriate"
                instance.confidence = 0.0
                instance.moderation_data_full = {"error": str(e)}
                instance.moderated_at = timezone.now()
