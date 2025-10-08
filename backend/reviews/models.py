from django.db import models
from django.utils import timezone


class Review(models.Model):
    STATUS_CHOICES = [
        ("allowed", "Allowed"),
        ("pending", "Pending"),
        ("to_be_deleted", "To Be Deleted"),
    ]

    RISK_CATEGORY_CHOICES = [
        ("appropriate", "Appropriate"),
        ("sexual", "Sexual"),
        ("hate", "Hate"),
        ("harassment", "Harassment"),
        ("self-harm", "Self-Harm"),
        ("sexual/minors", "Sexual/Minors"),
        ("hate/threatening", "Hate/Threatening"),
        ("violence/graphic", "Violence/Graphic"),
        ("self-harm/intent", "Self-Harm/Intent"),
        ("self-harm/instructions", "Self-Harm/Instructions"),
        ("harassment/threatening", "Harassment/Threatening"),
        ("violence", "Violence"),
        ("spam", "Spam"),
    ]

    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    moderated_at = models.DateTimeField(null=True, blank=True, default=timezone.now)

    # Moderation data
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    risk_category = models.CharField(
        max_length=50,
        choices=RISK_CATEGORY_CHOICES,
        default="appropriate",
    )
    confidence = models.FloatField(default=0.0)
    moderation_data_full = models.JSONField(
        default=dict
    )  # Store full data, just in case.

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.risk_category}: {self.confidence:.2f}"

    # def moderate(self):
    #     """
    #     Manual moderation fallback. For testing purposes only.
    #     """
    #     from .services.moderation_service import OpenAIModerationService

    #     service = OpenAIModerationService()
    #     result = service.moderate(self.content)

    #     self.status = result["status"]
    #     self.risk_category = result["risk_category"]
    #     self.confidence = result["confidence"]
    #     self.moderation_data_full = result["moderation_data_full"]
    #     self.moderated_at = timezone.now()

    #     self.save()
    #     return self.status
